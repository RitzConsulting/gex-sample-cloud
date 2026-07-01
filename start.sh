#!/usr/bin/env bash
# gex-sample-cloud — one-command local run (macOS/Linux).
set -euo pipefail
cd "$(dirname "$0")"

[ -d .venv ] || python3 -m venv .venv
.venv/bin/python -m pip install --quiet -r requirements-dev.txt

export PORT=8080
echo ""
echo "GEX sample running at http://127.0.0.1:8080   (press Ctrl+C to stop)"
echo ""
( sleep 3; python3 -m webbrowser "http://127.0.0.1:8080" >/dev/null 2>&1 || true ) &
exec .venv/bin/python run.py
