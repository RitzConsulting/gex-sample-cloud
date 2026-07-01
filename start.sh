#!/usr/bin/env bash
# gex-sample-cloud — one-command local run (macOS/Linux).
# Stays open and shows the error if anything fails.
set -uo pipefail
cd "$(dirname "$0")"
fail() { echo; echo "ERROR: $1"; read -rp "Press Enter to close..."; exit 1; }

[ -d .venv ] || python3 -m venv .venv || fail "could not create virtualenv (is python3 installed?)"
.venv/bin/python -m pip install -q -r requirements-dev.txt || fail "pip install failed"

export PORT=8080
echo ""
echo "GEX sample running at http://127.0.0.1:8080   (press Ctrl+C to stop)"
echo ""
( sleep 3; python3 -m webbrowser "http://127.0.0.1:8080" >/dev/null 2>&1 || true ) &
.venv/bin/python run.py; ec=$?
[ $ec -eq 0 ] || [ $ec -eq 130 ] || fail "the app exited ($ec) — see above"
