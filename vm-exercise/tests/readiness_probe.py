"""Readiness probe for the VM sample.

Checks the deployed worker is alive, persisting data through gateway outages,
and recovering. Point it at the worker's URL (via your nginx/TLS front, or an
SSH tunnel to 127.0.0.1:8070).

    BASE_URL=https://<vm-or-tunnel> python readiness_probe.py

Liveness is measured over a window (tick_count must advance), because the
gateway intentionally has ~10s/60s outages — a single sample can catch a dip.
"""

import os
import sys
import time

import requests

BASE = os.environ.get("BASE_URL", "http://127.0.0.1:8070").rstrip("/")
TIMEOUT = 10


def status():
    return requests.get(f"{BASE}/status", timeout=TIMEOUT).json()


def main():
    try:
        s1 = status()
    except Exception as e:
        sys.exit(f"FAIL: cannot reach {BASE}/status: {e}")

    print(f"initial: tick_count={s1['tick_count']} reconnects={s1['reconnects']} "
          f"connected={s1['connected']}")

    print("observing for ~15s (spanning a gateway outage window)...")
    time.sleep(15)
    s2 = status()
    print(f"later:   tick_count={s2['tick_count']} reconnects={s2['reconnects']} "
          f"connected={s2['connected']}")

    if s2["tick_count"] <= s1["tick_count"]:
        sys.exit("FAIL: tick_count did not advance — worker is not persisting data.")

    # /health should be 200 during an 'up' window at least once.
    ok = False
    for _ in range(12):
        if requests.get(f"{BASE}/health", timeout=TIMEOUT).status_code == 200:
            ok = True
            break
        time.sleep(1)
    if not ok:
        sys.exit("FAIL: /health never returned 200 — worker stayed degraded.")

    print(f"PASS: worker alive + persisting (delta={s2['tick_count'] - s1['tick_count']} ticks, "
          f"reconnects handled={s2['reconnects']}).")


if __name__ == "__main__":
    main()
