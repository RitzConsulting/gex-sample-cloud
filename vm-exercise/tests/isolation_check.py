"""Stage 2 isolation check — two-VM private networking.

Two modes prove the gateway is reachable by the engine PRIVATELY but not by the
public internet:

    # on the ENGINE VM (worker running locally on :8070) — should PASS:
    python isolation_check.py engine

    # from OUTSIDE (laptop / Cloud Shell / a non-allowed host) — should PASS by
    # FAILING to connect to the gateway's public endpoint:
    GATEWAY_PUBLIC=http://<gateway-public-ip>:8071 python isolation_check.py public
"""

import os
import sys

import requests

TIMEOUT = 6


def engine():
    try:
        s = requests.get("http://127.0.0.1:8070/status", timeout=TIMEOUT).json()
    except Exception as e:
        sys.exit(f"FAIL: worker not reachable on the engine VM (:8070): {e}")
    if s.get("tick_count", 0) > 0 and s.get("connected"):
        print(f"PASS: engine is reaching the gateway over the private network "
              f"(tick_count={s['tick_count']}, connected=True).")
    else:
        sys.exit(
            "FAIL: engine is NOT receiving ticks "
            f"(connected={s.get('connected')}, tick_count={s.get('tick_count')}). "
            "Check GATEWAY_URL=<gateway-private-ip> and the firewall allow rule."
        )


def public():
    url = os.environ.get("GATEWAY_PUBLIC")
    if not url:
        sys.exit("set GATEWAY_PUBLIC=http://<gateway-public-ip>:8071")
    try:
        requests.get(f"{url.rstrip('/')}/health", timeout=TIMEOUT)
    except requests.exceptions.RequestException:
        print(f"PASS: gateway is NOT reachable from outside ({url}) — correctly private.")
        return
    sys.exit(f"FAIL: gateway IS reachable from outside at {url} — it must be private-only. "
             "Remove any 0.0.0.0/0 allow rule / external IP on the gateway port.")


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in ("engine", "public"):
        sys.exit("usage: isolation_check.py [engine|public]")
    (engine if sys.argv[1] == "engine" else public)()


if __name__ == "__main__":
    main()
