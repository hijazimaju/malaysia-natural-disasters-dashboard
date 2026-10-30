#!/usr/bin/env bash
# Run the dashboard. Creates the venv on first run if missing.
set -euo pipefail
cd "$(dirname "$0")"
if [ ! -d .venv ]; then
  if command -v uv >/dev/null 2>&1; then uv venv .venv; else python3 -m venv .venv; fi
  .venv/bin/pip install -r requirements.txt
fi
exec .venv/bin/streamlit run app.py
