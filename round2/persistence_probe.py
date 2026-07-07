"""Round 2 self-check probe — verify ingested data survives a redeploy.

Round 1 stored data on Cloud Run's ephemeral filesystem, so a redeploy wiped it.
Round 2 requires durable storage (GCS-backed SQLite or Cloud SQL). This probe
proves it, black-box, in three steps:

    pip install requests

    # 1) seed a unique marker (needs your production write key)
    BASE_URL=https://<svc> SYNC_API_KEY=<key> python persistence_probe.py seed --marker r2-demo

    # 2) REDEPLOY the service (new revision / cold start)

    # 3) verify the marker survived (public GET, no key needed)
    BASE_URL=https://<svc> python persistence_probe.py verify --marker r2-demo

Use a fresh --marker each run so an old record can't give a false pass.
This is the same probe the evaluator uses. Exit 0 = pass, non-zero = fail.
"""

import argparse
import os
import sys

import requests

TIMEOUT = 20


def _base():
    b = os.environ.get("BASE_URL", "").rstrip("/")
    if not b:
        sys.exit("ERROR: set BASE_URL=https://your-service...")
    return b


def seed(marker):
    key = os.environ.get("SYNC_API_KEY")
    if not key:
        sys.exit("ERROR: set SYNC_API_KEY to seed (the production write key).")
    strategy = f"PERSIST-{marker}"
    r = requests.post(
        f"{_base()}/api/sync/push",
        headers={"X-Sync-Key": key},
        json={"table": "trade_ideas", "rows": [{
            "ts": "2026-07-06T00:00:00Z", "strategy": strategy,
            "short_strike": 6000, "long_strike": 5985, "credit": 1.0, "status": "open",
        }]},
        timeout=TIMEOUT,
    )
    if r.status_code != 200:
        sys.exit(f"seed FAILED: HTTP {r.status_code} {r.text[:200]}")
    print(f"seeded strategy='{strategy}'.")
    print(f"Now redeploy the service, then run:  verify --marker {marker}")


def verify(marker):
    strategy = f"PERSIST-{marker}"
    r = requests.get(f"{_base()}/api/trade-ideas", timeout=TIMEOUT)
    if r.status_code != 200:
        sys.exit(f"verify FAILED to read /api/trade-ideas: HTTP {r.status_code}")
    rows = r.json() if r.headers.get("content-type", "").startswith("application/json") else []
    if any(str(row.get("strategy", "")) == strategy for row in rows):
        print(f"PASS: '{strategy}' survived the redeploy - persistence works.")
        return
    sys.exit(
        f"FAIL: '{strategy}' NOT found after redeploy - data did not persist "
        f"(checked {len(rows)} recent rows). If dummy seed data reappeared, the DB was wiped."
    )


def main():
    p = argparse.ArgumentParser(description="Round 2 persistence self-check probe")
    p.add_argument("mode", choices=["seed", "verify"])
    p.add_argument("--marker", required=True, help="unique tag for this run, e.g. r2-2026-07-07")
    args = p.parse_args()
    (seed if args.mode == "seed" else verify)(args.marker)


if __name__ == "__main__":
    main()
