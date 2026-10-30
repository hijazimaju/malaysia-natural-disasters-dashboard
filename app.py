"""Malaysia Natural Disasters Dashboard.

Data: EM-DAT (CRED/UCLouvain) country profiles via Humanitarian Data Exchange,
dataset updated 2026-10-28. One row per (year, disaster subtype) for Malaysia.
Run: ./run.sh   (or: .venv/bin/streamlit run app.py)
"""

from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

DATA_PATH = Path(__file__).with_name("malaysia_natural_disasters.csv")

st.set_page_config(page_title="Malaysia Natural Disasters", layout="wide")


@st.cache_data
def load_data() -> pd.DataFrame:
    df = pd.read_csv(DATA_PATH)
    # Nullable integer dtypes so missing values stay missing (not silently 0)
    for col in ["affected", "deaths", "damage_usd_original", "damage_usd_adjusted"]:
        df[col] = df[col].astype("Int64")
    return df


df = load_data()

st.title("🇲🇾 Malaysia Natural Disasters Dashboard")
st.caption("Source: EM-DAT (CRED/UCLouvain) via Humanitarian Data Exchange · updated 2026-10-28")

# ---------- Sidebar filters ----------
st.sidebar.header("Filters")
year_min, year_max = int(df["year"].min()), int(df["year"].max())
years = st.sidebar.slider("Year range", year_min, year_max, (year_min, year_max))
types = st.sidebar.multiselect(
    "Disaster type",
    options=sorted(df["disaster_type"].unique()),
    default=sorted(df["disaster_type"].unique()),
)
metric = st.sidebar.selectbox(
    "Trend metric",
    ["events", "affected", "deaths", "damage_usd_adjusted"],
    format_func=lambda c: {
        "events": "Events",
        "affected": "People affected",
        "deaths": "Deaths",
        "damage_usd_adjusted": "Damage (USD, inflation-adjusted)",
    }[c],
)

flt = df[(df["year"].between(*years)) & (df["disaster_type"].isin(types))]
if flt.empty:
    st.warning("No records match the selected filters.")
    st.stop()

# ---------- KPI row ----------
k1, k2, k3, k4 = st.columns(4)
k1.metric("Events", f"{int(flt['events'].sum()):,}")
k2.metric("People affected", f"{int(flt['affected'].sum(skipna=True)):,}")
k3.metric("Deaths", f"{int(flt['deaths'].sum(skipna=True)):,}")
k4.metric(
    "Damage (adj. USD)",
    f"${int(flt['damage_usd_adjusted'].sum(skipna=True)):,}",
)
st.caption(
    "KPIs sum only reported values — blank cells (missing data) are excluded, not treated as zero. "
    f"Missing: affected {int(flt['affected'].isna().sum())}, deaths {int(flt['deaths'].isna().sum())}, "
    f"damage {int(flt['damage_usd_adjusted'].isna().sum())} rows."
)

# ---------- Trend chart ----------
trend = (
    flt.groupby(["year", "disaster_type"], as_index=False)[metric]
    .sum(min_count=1)  # keep NaN if every value in the group is missing
    .sort_values("year")
)
fig = px.bar(
    trend,
    x="year",
    y=metric,
    color="disaster_type",
    title=f"{metric.replace('_', ' ').title()} by year and disaster type",
    labels={"year": "Year", "disaster_type": "Disaster type"},
)
fig.update_layout(bargap=0.3)
st.plotly_chart(fig, use_container_width=True)

# ---------- Detail table ----------
st.subheader("Detail records")
show = flt.sort_values(["year", "disaster_type", "disaster_subtype"]).copy()
show["affected"] = show["affected"].map(lambda v: f"{int(v):,}" if pd.notna(v) else "—")
show["deaths"] = show["deaths"].map(lambda v: f"{int(v):,}" if pd.notna(v) else "—")
show["damage_usd_adjusted"] = show["damage_usd_adjusted"].map(
    lambda v: f"${int(v):,}" if pd.notna(v) else "—"
)
st.dataframe(
    show[
        ["year", "disaster_subgroup", "disaster_type", "disaster_subtype",
         "events", "affected", "deaths", "damage_usd_adjusted"]
    ],
    use_container_width=True,
    hide_index=True,
)

with st.expander("⚠️ Data pitfalls (read before quoting numbers)"):
    st.markdown(
        """
- **EM-DAT inclusion threshold:** only disasters with ≥10 deaths, ≥100 people
  affected, a declared state of emergency, or an international appeal are recorded.
  Everyday small floods are *not* in this data.
- **Reporting bias:** the upward trend over time largely reflects better reporting,
  not necessarily more disasters.
- **Missing values are blank, not zero:** 14 rows lack death counts and 31 rows lack
  damage estimates. Totals exclude them.
- **2025 is partial:** the year is still in progress at the last dataset update
  (2026-10-28).
- **Damage figures** are EM-DAT estimates in USD (original year) and
  inflation-adjusted USD via CPI.
"""
    )
