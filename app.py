"""Papan Pemuka Bencana Alam Malaysia — versi Live.

Gabungan:
- LIVE: peristiwa semasa GDACS (global, dikemas kini berterusan) + gempa bumi
  terkini USGS berhampiran Malaysia + operasi kecemasan IFRC.
  Auto-refresh setiap 10 minit.
- SEJARAH: data EM-DAT 2000–2025 (CSV statik dalam repo).

Sumber live:
- GDACS (UN/OCHA & EC JRC): https://www.gdacs.org/gdacsapi/api/events/geteventlist/SEARCH
- USGS Earthquake Hazards Program: https://earthquake.usgs.gov/fdsnws/event/1/
- IFRC GO (Persekutuan Antarabangsa Palang Merah): https://goadmin.ifrc.org/api/v2/event/
Jalankan: ./run.sh
"""

from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import plotly.express as px
import requests
import streamlit as st
from streamlit_autorefresh import st_autorefresh

DATA_PATH = Path(__file__).with_name("malaysia_natural_disasters.csv")
REFRESH_MS = 10 * 60 * 1000  # 10 minit

TYPE_LABEL = {
    "EQ": "Gempa bumi",
    "TC": "Siklon tropika",
    "FL": "Banjir",
    "WF": "Kebakaran hutan",
    "VO": "Gunung berapi",
    "DR": "Kemarau",
}
ALERT_COLOR = {"Red": "#d62728", "Orange": "#ff7f0e", "Green": "#2ca02c"}

st.set_page_config(page_title="World Natural Disaster Dashboard", layout="wide")

# Auto-refresh seluruh app; data di-cache 10 minit (ttl) supaya API tidak dibelasah.
st_autorefresh(interval=REFRESH_MS, key="live_refresh")


def _now_my():
    return datetime.now(timezone.utc).astimezone()


@st.cache_data(ttl=600)
def fetch_gdacs() -> pd.DataFrame:
    """Peristiwa bencana semasa dari GDACS (dunia)."""
    r = requests.get(
        "https://www.gdacs.org/gdacsapi/api/events/geteventlist/SEARCH",
        timeout=25,
    )
    r.raise_for_status()
    feats = r.json().get("features", [])
    rows = []
    for f in feats:
        p = f.get("properties", {}) or {}
        g = f.get("geometry", {}) or {}
        coords = g.get("coordinates") or [None, None]
        countries = p.get("country") or ""
        affected = p.get("affectedcountries") or ""
        url_raw = p.get("url")
        url = url_raw.get("report") if isinstance(url_raw, dict) else url_raw
        rows.append(
            {
                "jenis_kod": p.get("eventtype"),
                "jenis": TYPE_LABEL.get(p.get("eventtype"), p.get("eventtype")),
                "nama": p.get("eventname") or p.get("name") or "-",
                "negara": countries,
                "aras": p.get("alertlevel") or "-",
                "dari": p.get("fromdate"),
                "hingga": p.get("todate"),
                "lon": coords[0],
                "lat": coords[1],
                "url": url,
                "melibatkan_my": "Malaysia" in f"{countries} {affected}",
            }
        )
    df = pd.DataFrame(rows)
    if not df.empty:
        df["dari_dt"] = pd.to_datetime(df["dari"], errors="coerce", utc=True)
        df = df.sort_values("dari_dt", ascending=False).reset_index(drop=True)
    df.attrs["fetched_at"] = _now_my()
    return df


@st.cache_data(ttl=600)
def fetch_usgs() -> pd.DataFrame:
    """Gempa M4+ dalam 30 hari di sekitar Malaysia (9°S–8°N, 99°E–106°E)."""
    r = requests.get(
        "https://earthquake.usgs.gov/fdsnws/event/1/query",
        params={
            "format": "geojson",
            "starttime": (
                datetime.now(timezone.utc).date()
                - pd.Timedelta(days=30)
            ).isoformat(),
            "minlatitude": -9, "maxlatitude": 8,
            "minlongitude": 99, "maxlongitude": 106,
            "minmagnitude": 4, "orderby": "time", "limit": 50,
        },
        timeout=25,
    )
    r.raise_for_status()
    feats = r.json().get("features", [])
    rows = []
    for f in feats:
        p = f.get("properties", {}) or {}
        c = (f.get("geometry", {}) or {}).get("coordinates") or [None, None, None]
        rows.append(
            {
                "masa": pd.to_datetime(p.get("time"), unit="ms", utc=True),
                "magnitud": p.get("mag"),
                "lokasi": p.get("place"),
                "kedalaman_km": c[2],
                "lon": c[0], "lat": c[1],
                "url": p.get("url"),
            }
        )
    df = pd.DataFrame(rows).sort_values("masa", ascending=False).reset_index(drop=True)
    df.attrs["fetched_at"] = _now_my()
    return df


@st.cache_data(ttl=1800)
def fetch_ifrc() -> pd.DataFrame:
    """Operasi kecemasan terkini IFRC (dunia) — Persekutuan Antarabangsa
    Palang Merah & Bulan Sabit Merah."""
    r = requests.get(
        "https://goadmin.ifrc.org/api/v2/event/",
        params={"ordering": "-created_at", "limit": 150},
        timeout=25,
    )
    r.raise_for_status()
    rows = []
    for ev in r.json().get("results", []):
        countries = ev.get("countries") or []
        isos = [str(c.get("iso") or "") for c in countries]
        cnames = ", ".join(c.get("name") or "" for c in countries) or "-"
        rows.append(
            {
                "tarikh": (ev.get("disaster_start_date") or ev.get("created_at") or "")[:10],
                "peristiwa": ev.get("name") or "-",
                "jenis": (ev.get("dtype") or {}).get("name") or "-",
                "negara": cnames,
                "tahap": ev.get("ifrc_severity_level_display") or "-",
                "terjejas": ev.get("num_affected"),
                "url": f"https://go.ifrc.org/emergencies/{ev.get('id')}",
                "melibatkan_my": any(i in ("MYS", "MY") for i in isos)
                or "malaysia" in (ev.get("name") or "").lower(),
            }
        )
    df = pd.DataFrame(rows)
    df.attrs["fetched_at"] = _now_my()
    return df


@st.cache_data
def load_emdat() -> pd.DataFrame:
    df = pd.read_csv(DATA_PATH)
    for col in ["affected", "deaths", "damage_usd_original", "damage_usd_adjusted"]:
        df[col] = df[col].astype("Int64")
    return df


def live_badge(ts):
    st.markdown(
        f"🟢 **LIVE** — data semasa ditarik pada "
        f"{ts.strftime('%d %b %Y, %H:%M')} (auto-refresh setiap 10 minit)",
    )


NEWS_QUERIES = [
    ("banjir Malaysia", "ms"),
    ("bencana alam Malaysia", "ms"),
    ("natural disaster Malaysia", "en"),
]


@st.cache_data(ttl=1800)
def fetch_news() -> pd.DataFrame:
    """Berita terkini bencana alam dari Google News RSS (pelbagai outlet berlesen)."""
    import xml.etree.ElementTree as ET
    from email.utils import parsedate_to_datetime

    headers = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                             "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"}
    rows = []
    for q, lang in NEWS_QUERIES:
        ceid = "MY%3Ams" if lang == "ms" else "MY%3Aen"
        url = (f"https://news.google.com/rss/search?q={q}%20when%3A30d"
               f"&hl={lang}&gl=MY&ceid={ceid}")
        try:
            r = requests.get(url, headers=headers, timeout=20)
            r.raise_for_status()
            items = ET.fromstring(r.content).find("channel").findall("item")
        except Exception:  # noqa: BLE001 — langkau query yang gagal
            continue
        for it in items:
            title = (it.findtext("title") or "").rsplit(" - ", 1)[0].strip()
            src_el = it.find("source")
            link = (it.findtext("link") or "").strip()
            try:
                pub = parsedate_to_datetime(it.findtext("pubDate"))
            except Exception:  # noqa: BLE001
                pub = None
            if title and link:
                rows.append({
                    "tajuk": title,
                    "sumber": src_el.text if src_el is not None else "-",
                    "masa": pub, "pautan": link,
                })
    df = pd.DataFrame(rows)
    if not df.empty:
        # hanya outlet berita — buang sumber media sosial
        sosmed = ("facebook", "youtube", "tiktok", "instagram", "twitter", "x ")
        df = df[~df["sumber"].str.lower().str.startswith(sosmed)]
        df["kunci"] = df["tajuk"].str.lower().str[:60]
        df = (df.sort_values("masa", ascending=False)
                .drop_duplicates("kunci").head(20).reset_index(drop=True))
    df.attrs["fetched_at"] = _now_my()
    return df


# ================= HEADER =================
st.title("🌍 WORLD NATURAL DISASTER DASHBOARD")
tab_live, tab_sejarah = st.tabs(["🔴 Live Sekarang", "📚 Sejarah 2000–2025 (EM-DAT)"])

# ================= TAB LIVE =================
with tab_live:
    try:
        g = fetch_gdacs()
        gdacs_ok = not g.empty
    except Exception as e:  # noqa: BLE001 — papar amaran, jangan crash
        g, gdacs_ok = pd.DataFrame(), False
        st.warning(f"Gagal tarik data GDACS buat masa ini ({e}). Cuba lagi sebentar.")
    try:
        q = fetch_usgs()
        usgs_ok = not q.empty
    except Exception as e:  # noqa: BLE001
        q, usgs_ok = pd.DataFrame(), False
        st.warning(f"Gagal tarik data gempa USGS buat masa ini ({e}).")

    if gdacs_ok:
        live_badge(g.attrs["fetched_at"])
    st.caption(
        "Sumber live: GDACS (PBB/OCHA & EC-JRC) untuk peristiwa bencana semasa dunia; "
        "USGS untuk gempa bumi. Angka GDACS ialah anggaran impak automatik, bukan angka rasmi."
    )

    if gdacs_ok:
        n_red = int((g["aras"] == "Red").sum())
        g_my = g[g["melibatkan_my"]]
        latest = g.iloc[0]

        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Peristiwa aktif (dunia)", f"{len(g):,}")
        k2.metric("Melibatkan Malaysia", f"{len(g_my):,}")
        k3.metric("Amaran merah", f"{n_red:,}")
        k4.metric(
            "Peristiwa terkini",
            latest["jenis"],
            f"{latest['nama'][:32]}",
        )

        # --- Peta peristiwa ---
        st.subheader("🗺️ Peta peristiwa semasa")
        gm = g.dropna(subset=["lat", "lon"]).copy()
        gm["warna"] = gm["aras"].map(ALERT_COLOR).fillna("#7f7f7f")
        fig = px.scatter_map(
            gm, lat="lat", lon="lon", color="aras",
            color_discrete_map=ALERT_COLOR,
            hover_name="nama",
            hover_data={"jenis": True, "negara": True, "dari": True,
                        "lat": False, "lon": False, "aras": False},
            zoom=1, height=520,
            title="Peristiwa bencana aktif (GDACS) — warna ikut tahap amaran",
        )
        fig.update_layout(map_style="open-street-map",
                          margin=dict(l=0, r=0, t=40, b=0))
        st.plotly_chart(fig, use_container_width=True)
        st.caption("Peta: OpenStreetMap.")

        # --- Jadual peristiwa terkini ---
        st.subheader("📋 Peristiwa terkini")
        show = g.head(25).copy()
        show["tarikh"] = show["dari_dt"].dt.strftime("%d %b %Y")
        st.dataframe(
            show[["tarikh", "jenis", "nama", "negara", "aras"]].rename(columns={
                "tarikh": "Tarikh", "jenis": "Jenis", "nama": "Nama peristiwa",
                "negara": "Negara", "aras": "Amaran",
            }),
            use_container_width=True, hide_index=True,
        )
        if not g_my.empty:
            st.subheader("⚠️ Melibatkan Malaysia")
            my = g_my.copy()
            my["tarikh"] = my["dari_dt"].dt.strftime("%d %b %Y")
            st.dataframe(
                my[["tarikh", "jenis", "nama", "aras", "url"]].rename(columns={
                    "tarikh": "Tarikh", "jenis": "Jenis", "nama": "Nama peristiwa",
                    "aras": "Amaran", "url": "Pautan GDACS",
                }),
                use_container_width=True, hide_index=True,
                column_config={"Pautan GDACS": st.column_config.LinkColumn()},
            )

        # --- Peta Malaysia: kawasan terkesan ---
        st.subheader("🇲🇾 Peta Malaysia — kawasan terkesan")
        pts = []
        if not g_my.empty:
            for _, r in g_my.dropna(subset=["lat", "lon"]).iterrows():
                pts.append({"lat": r["lat"], "lon": r["lon"],
                            "kategori": f"GDACS: {r['jenis']} ({r['aras']})",
                            "label": f"{r['nama']} — {r['jenis']}, amaran {r['aras']}"})
        if usgs_ok and not q.empty:
            for _, r in q.dropna(subset=["lat", "lon"]).iterrows():
                pts.append({"lat": r["lat"], "lon": r["lon"],
                            "kategori": "USGS: Gempa bumi",
                            "label": f"M{r['magnitud']:.1f} — {r['lokasi']}"})
        if pts:
            pm = pd.DataFrame(pts)
            figm = px.scatter_map(
                pm, lat="lat", lon="lon", color="kategori",
                hover_name="label", zoom=5,
                center=dict(lat=4.2, lon=102.2), height=520,
                title="Titik peristiwa GDACS & gempa USGS di sekitar Malaysia",
                color_discrete_map={
                    "GDACS: Banjir (Red)": "#d62728",
                    "GDACS: Banjir (Orange)": "#ff7f0e",
                    "USGS: Gempa bumi": "#1f77b4",
                },
            )
            figm.update_layout(map_style="open-street-map",
                               margin=dict(l=0, r=0, t=40, b=0))
            # kategori GDACS lain yang tidak dijangka — warna lalai
            st.plotly_chart(figm, use_container_width=True)
            st.caption("Peta: OpenStreetMap. Titik merah/oren = peristiwa GDACS "
                       "melibatkan Malaysia; biru = gempa USGS 30 hari.")
        elif gdacs_ok:
            st.info("Tiada titik peristiwa melibatkan Malaysia buat masa ini.")

    # --- IFRC: operasi kecemasan antarabangsa ---
    st.divider()
    st.subheader("🟥 IFRC — Operasi kecemasan antarabangsa terkini")
    try:
        ifrc = fetch_ifrc()
        ifrc_ok = True
    except Exception as e:
        ifrc_ok = False
        ifrc_err = e
    if ifrc_ok and not ifrc.empty:
        st.caption(
            f"Ditarik pada {ifrc.attrs['fetched_at'].strftime('%d %b %Y, %H:%M')} — "
            "Persekutuan Antarabangsa Palang Merah & Bulan Sabit Merah (IFRC), "
            "operasi kecemasan & rayuan bantuan terkini di seluruh dunia."
        )
        st.dataframe(
            ifrc.head(15)[["tarikh", "peristiwa", "jenis", "negara", "tahap"]].rename(columns={
                "tarikh": "Tarikh", "peristiwa": "Operasi", "jenis": "Jenis",
                "negara": "Negara", "tahap": "Tahap",
            }),
            use_container_width=True, hide_index=True,
        )
        ifrc_my = ifrc[ifrc["melibatkan_my"]]
        if not ifrc_my.empty:
            st.subheader("⚠️ Operasi IFRC melibatkan Malaysia")
            st.dataframe(
                ifrc_my[["tarikh", "peristiwa", "jenis", "tahap", "url"]].rename(columns={
                    "tarikh": "Tarikh", "peristiwa": "Operasi", "jenis": "Jenis",
                    "tahap": "Tahap", "url": "Pautan IFRC GO",
                }),
                use_container_width=True, hide_index=True,
                column_config={"Pautan IFRC GO": st.column_config.LinkColumn()},
            )
    elif ifrc_ok:
        st.info("Tiada operasi IFRC direkodkan buat masa ini.")
    else:
        st.warning(f"Data IFRC gagal dimuatkan: {ifrc_err}. Paparan lain tidak terjejas.")

    # --- Gempa USGS ---
    st.divider()
    st.subheader("🌊 Gempa bumi terkini berhampiran Malaysia (USGS, 30 hari)")
    if usgs_ok:
        st.caption(
            f"Ditarik pada {q.attrs['fetched_at'].strftime('%d %b %Y, %H:%M')} — "
            "kawasan 9°S–8°N, 99°E–106°E (termasuk Sumatera; gegaran boleh dirasai di Malaysia)."
        )
        c1, c2, c3 = st.columns(3)
        c1.metric("Gempa M4+ (30 hari)", f"{len(q)}")
        c2.metric("Magnitud terbesar", f"M{q['magnitud'].max():.1f}")
        latest_q = q.iloc[0]
        c3.metric("Terkini", f"M{latest_q['magnitud']:.1f}",
                  latest_q["lokasi"][:35])

        qm = q.dropna(subset=["lat", "lon"])
        if not qm.empty:
            fig2 = px.scatter_map(
                qm, lat="lat", lon="lon", size="magnitud",
                hover_name="lokasi",
                hover_data={"magnitud": True, "kedalaman_km": True,
                            "lat": False, "lon": False},
                color_discrete_sequence=["#d62728"],
                zoom=4, center=dict(lat=2.5, lon=103), height=480,
                title="Episenter gempa (saiz ikut magnitud)",
                size_max=22,
            )
            fig2.update_layout(map_style="open-street-map",
                               margin=dict(l=0, r=0, t=40, b=0))
            st.plotly_chart(fig2, use_container_width=True)
            st.caption("Peta: OpenStreetMap.")

        qs = q.head(15).copy()
        qs["masa_str"] = qs["masa"].dt.strftime("%d %b %Y %H:%M UTC")
        st.dataframe(
            qs[["masa_str", "magnitud", "lokasi", "kedalaman_km", "url"]].rename(columns={
                "masa_str": "Masa", "magnitud": "Magnitud", "lokasi": "Lokasi",
                "kedalaman_km": "Kedalaman (km)", "url": "Pautan USGS",
            }),
            use_container_width=True, hide_index=True,
            column_config={"Pautan USGS": st.column_config.LinkColumn()},
        )
    else:
        st.info("Data gempa tidak dapat ditarik buat masa ini.")

    with st.expander("⚠️ Nota tentang data live"):
        st.markdown(
            """
- **GDACS**: tahap amaran (Green/Orange/Red) ialah anggaran automatik berdasarkan
  model impak — bukan pengisytiharan rasmi kerajaan.
- **Tarikh banjir** GDACS kadangkala ialah tarikh ramalan model (boleh ke hadapan).
- **USGS**: kebanyakan gempa dalam bbox ini berpusat di Sumatera, Indonesia —
  gegarannya dirasai di Semenanjung, tetapi ia bukan gempa "di Malaysia".
- Data live di-cache 10 minit dan app refresh automatik setiap 10 minit.
- Berita: agregat Google News RSS dari outlet berlesen (Bernama, Astro Awani,
  BH, Utusan, Sinar Harian dll.), dikemas kini setiap 30 minit.
"""
        )

    # --- Berita terkini ---
    st.divider()
    st.subheader("📰 Berita terkini bencana alam")
    try:
        news = fetch_news()
        news_ok = not news.empty
    except Exception as e:  # noqa: BLE001
        news, news_ok = pd.DataFrame(), False
        st.warning(f"Gagal tarik berita buat masa ini ({e}).")
    if news_ok:
        st.caption(
            f"Dikemas kini {news.attrs['fetched_at'].strftime('%d %b %Y, %H:%M')} · "
            "sumber: Google News RSS (pelbagai outlet berlesen)."
        )
        for _, n in news.iterrows():
            masa = n["masa"].strftime("%d %b %H:%M") if pd.notna(n["masa"]) else ""
            st.markdown(f"**[{n['sumber']}]** [{n['tajuk']}]({n['pautan']}) "
                        f"<sub>{masa}</sub>", unsafe_allow_html=True)
    else:
        st.info("Tiada berita dapat ditarik buat masa ini.")

# ================= TAB SEJARAH =================
with tab_sejarah:
    df = load_emdat()
    st.caption(
        "Sumber: EM-DAT (CRED/UCLouvain) via Humanitarian Data Exchange · "
        "dikemas kini 2026-10-28 · fail CSV statik dalam repo"
    )
    st.sidebar.header("Penapis (Sejarah)")
    year_min, year_max = int(df["year"].min()), int(df["year"].max())
    years = st.sidebar.slider("Julat tahun", year_min, year_max, (year_min, year_max))
    types = st.sidebar.multiselect(
        "Jenis bencana",
        options=sorted(df["disaster_type"].unique()),
        default=sorted(df["disaster_type"].unique()),
    )
    metric = st.sidebar.selectbox(
        "Metrik trend",
        ["events", "affected", "deaths", "damage_usd_adjusted"],
        format_func=lambda c: {
            "events": "Bilangan peristiwa",
            "affected": "Mangsa terjejas",
            "deaths": "Kematian",
            "damage_usd_adjusted": "Kerosakan (USD selaras inflasi)",
        }[c],
    )
    metric_bm = {
        "events": "Bilangan peristiwa", "affected": "Mangsa terjejas",
        "deaths": "Kematian", "damage_usd_adjusted": "Kerosakan (USD selaras inflasi)",
    }[metric]

    flt = df[(df["year"].between(*years)) & (df["disaster_type"].isin(types))]
    if flt.empty:
        st.warning("Tiada rekod sepadan dengan penapis.")
        st.stop()

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Peristiwa", f"{int(flt['events'].sum()):,}")
    k2.metric("Mangsa terjejas", f"{int(flt['affected'].sum(skipna=True)):,}")
    k3.metric("Kematian", f"{int(flt['deaths'].sum(skipna=True)):,}")
    k4.metric("Kerosakan (USD selaras)",
              f"${int(flt['damage_usd_adjusted'].sum(skipna=True)):,}")
    st.caption(
        "KPI hanya menjumlahkan nilai yang dilaporkan — sel kosong dikecualikan, "
        "bukan dianggap sifar."
    )

    trend = (
        flt.groupby(["year", "disaster_type"], as_index=False)[metric]
        .sum(min_count=1)
        .sort_values("year")
    )
    fig = px.bar(
        trend, x="year", y=metric, color="disaster_type",
        title=f"{metric_bm} mengikut tahun dan jenis bencana",
        labels={"year": "Tahun", "disaster_type": "Jenis bencana"},
    )
    fig.update_layout(bargap=0.3)
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Rekod detail")
    show = flt.sort_values(["year", "disaster_type"]).copy()
    show["affected"] = show["affected"].map(lambda v: f"{int(v):,}" if pd.notna(v) else "—")
    show["deaths"] = show["deaths"].map(lambda v: f"{int(v):,}" if pd.notna(v) else "—")
    show["damage_usd_adjusted"] = show["damage_usd_adjusted"].map(
        lambda v: f"${int(v):,}" if pd.notna(v) else "—")
    st.dataframe(
        show[["year", "disaster_subgroup", "disaster_type", "disaster_subtype",
              "events", "affected", "deaths", "damage_usd_adjusted"]].rename(columns={
            "year": "Tahun", "disaster_subgroup": "Subkumpulan",
            "disaster_type": "Jenis", "disaster_subtype": "Subjenis",
            "events": "Peristiwa", "affected": "Terjejas", "deaths": "Kematian",
            "damage_usd_adjusted": "Kerosakan (USD selaras)"}),
        use_container_width=True, hide_index=True,
    )
    with st.expander("⚠️ Perangkap data (baca sebelum petik angka)"):
        st.markdown(
            """
- EM-DAT hanya merekod bencana melepasi ambang (≥10 kematian, ≥100 terjejas,
  darurat diisytihar, atau rayuan antarabangsa). Banjir kecil harian tiada.
- Trend menaik sebahagian besarnya kesan liputan laporan yang makin baik.
- Nilai kosong bermaksud tiada data — bukan sifar.
- Data 2025 separa (tahun belum habis semasa kemas kini 2026-10-28).
"""
        )
