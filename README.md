# Bencana Alam Malaysia — Papan Pemuka Live 🇲🇾

Papan pemuka Streamlit dwibahasa (BM) yang menggabungkan data bencana **semasa
(live)** dan **sejarah**. Tiada data direka — semua angka dari sumber sebenar.

## Tab 🔴 Live Sekarang (auto-refresh setiap 10 minit)

- **GDACS** (PBB/OCHA & EC-JRC) — peristiwa bencana aktif seluruh dunia:
  KPI (aktif, melibatkan Malaysia, amaran merah), peta dunia interaktif
  berwarna ikut tahap amaran, jadual 25 peristiwa terkini, dan senarai khas
  peristiwa yang melibatkan Malaysia dengan pautan laporan GDACS.
- **USGS** — gempa bumi M4+ dalam 30 hari di sekitar Malaysia
  (9°S–8°N, 99°E–106°E, termasuk Sumatera): KPI, peta episenter (saiz ikut
  magnitud), jadual 15 gempa terkini dengan pautan USGS.
- **Peta Malaysia** — titik peristiwa GDACS yang melibatkan Malaysia dan
  gempa USGS, di atas peta OpenStreetMap berpusat di Malaysia.
- **Berita terkini** — agregat Google News RSS (30 hari) dari outlet berlesen
  (Bernama, Astro Awani, The Star, Berita Harian, Utusan, Sinar Harian,
  Harian Metro dll.): tajuk berpaut, sumber dan masa, dikemas kini setiap
  30 minit. Sumber media sosial ditapis keluar.

## Tab 📚 Sejarah 2000–2025 (EM-DAT)

`malaysia_natural_disasters.csv` — 43 rekod, satu baris setiap
(tahun, subjenis bencana). Penapis sidebar (julat tahun, jenis, metrik),
KPI, carta trend dan jadual detail.

- **Sumber:** EM-DAT (CRED/UCLouvain) via Humanitarian Data Exchange,
  dikemas kini 2026-10-28.

## Had data (penting)

- GDACS: tahap amaran ialah anggaran impak automatik, bukan angka rasmi;
  tarikh banjir kadangkala tarikh ramalan model.
- USGS: kebanyakan gempa dalam bbox ini berpusat di Sumatera — gegaran
  dirasai di Malaysia, bukan gempa "di Malaysia".
- EM-DAT: hanya bencana melepasi ambang (≥10 kematian / ≥100 terjejas /
  darurat); trend menaik sebahagiannya kesan liputan laporan yang makin baik;
  sel kosong = tiada data, bukan sifar; 2025 separa.

## Jalankan

```bash
./run.sh
```

buka http://localhost:8501.

## Deploy

App ini di-deploy di Streamlit Community Cloud dari repo ini (branch `main`,
fail `app.py`). Setiap push ke `main` trigger redeploy automatik.
