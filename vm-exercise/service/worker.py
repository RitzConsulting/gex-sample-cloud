"""Stateful worker — stands in for the trading engine.

It polls the (flaky) gateway, persists every tick to SQLite on a persistent
disk, keeps a heartbeat, and exposes /health + /status. It ALREADY handles
gateway outages with retry + exponential backoff and counts reconnects — your
job is the VM operations around it: run it reliably under systemd, keep its data
on a persistent disk (survives reboot), supervise the gateway, and alert when
it stays degraded. Do NOT weaken this resilience logic.
"""

import os
import threading
import time

import requests
from flask import Flask, jsonify

from db import get_conn, init_db

GATEWAY_URL = os.environ.get("GATEWAY_URL", "http://127.0.0.1:8071")
GATEWAY_TOKEN = os.environ.get("GATEWAY_TOKEN", "dev-gateway-token-change-me")
POLL_SEC = float(os.environ.get("POLL_SEC", "2"))
STALE_SEC = float(os.environ.get("STALE_SEC", "20"))  # health degrades past this
PORT = int(os.environ.get("PORT", "8070"))

_state = {"last_price": None, "last_tick_at": 0.0, "tick_count": 0,
          "reconnects": 0, "consecutive_failures": 0, "connected": False}
_lock = threading.Lock()


def poll_loop():
    backoff = 1.0
    was_connected = False
    while True:
        try:
            r = requests.get(f"{GATEWAY_URL}/tick",
                             headers={"X-Gateway-Token": GATEWAY_TOKEN}, timeout=5)
            if r.status_code != 200:
                raise RuntimeError(f"gateway HTTP {r.status_code}")
            price = r.json().get("price")
            conn = get_conn()
            conn.execute("INSERT INTO ticks (ts, price) VALUES (?, ?)", (time.time(), price))
            conn.commit()
            conn.close()
            with _lock:
                if not was_connected and _state["tick_count"] > 0:
                    _state["reconnects"] += 1
                _state["last_price"] = price
                _state["last_tick_at"] = time.time()
                _state["tick_count"] += 1
                _state["consecutive_failures"] = 0
                _state["connected"] = True
            was_connected = True
            backoff = 1.0
            time.sleep(POLL_SEC)
        except Exception:
            with _lock:
                _state["consecutive_failures"] += 1
                _state["connected"] = False
            was_connected = False
            time.sleep(min(backoff, 30))
            backoff *= 2


app = Flask(__name__)


@app.get("/health")
def health():
    with _lock:
        fresh = _state["tick_count"] > 0 and (time.time() - _state["last_tick_at"]) < STALE_SEC
    return (jsonify({"status": "ok"}), 200) if fresh else (jsonify({"status": "degraded"}), 503)


@app.get("/status")
def status():
    with _lock:
        s = dict(_state)
    s["heartbeat_age"] = round(time.time() - s["last_tick_at"], 1) if s["last_tick_at"] else None
    return jsonify(s)


# Start the polling thread at import time so it runs under gunicorn too
# (gunicorn imports `worker:app` and never calls a main()).
_started = False


def _ensure_started():
    global _started
    if _started:
        return
    _started = True
    init_db()
    threading.Thread(target=poll_loop, name="poll", daemon=True).start()


_ensure_started()


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=PORT)
