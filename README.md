# Malaysia Natural Disasters Dashboard

Self-contained Streamlit dashboard of natural disasters in Malaysia, built from
real EM-DAT data (no fabricated values).

## Data

`malaysia_natural_disasters.csv` — 43 records, 2000–2025, one row per
(year, disaster subtype).

- **Source:** EM-DAT – The International Disasters Database (CRED, UCLouvain),
  country profiles via the Humanitarian Data Exchange
- **Dataset updated:** 2026-10-28
- **Schema:** `year, country, iso, disaster_subgroup, disaster_type,
  disaster_subtype, events, affected, deaths, damage_usd_original,
  damage_usd_adjusted`
- **Missing data:** `affected` (2 rows), `deaths` (14 rows), damage columns
  (31 rows each) are blank where EM-DAT has no figure — blanks are *not* zero.

### Data pitfalls

- EM-DAT only records disasters meeting its threshold (≥10 deaths, ≥100
  affected, declared emergency, or international appeal). Small everyday floods
  are not included.
- The long-term upward trend largely reflects better reporting, not necessarily
  more disasters.
- 2025 data is partial (year in progress at last update).

## Run

```bash
./run.sh
```

Then open http://localhost:8501. `run.sh` creates `.venv` and installs pinned
dependencies from `requirements.txt` on first run.

Manual equivalent:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/streamlit run app.py
```

## Features

- Sidebar filters: year range, disaster type, trend metric
- KPI row: events, people affected, deaths, inflation-adjusted damage
- Plotly trend chart (stacked by disaster type)
- Detail table with missing values shown as —
