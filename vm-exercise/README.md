# gex-sample-vm

A tiny, dummy **VM lift-and-shift readiness exercise** — the second-stage sample
for the cloud-migration role. Where `gex-sample-cloud` rehearsed serverless
(Cloud Run + secrets + IAM), this one rehearses the **single-VM / stateful /
long-lived-broker-gateway** skills that **Path A** of the real migration needs.

Two stages:
- **[ASSIGNMENT.md](ASSIGNMENT.md)** — Stage 1: one hardened VM (systemd, persistent
  disk, supervise the flaky gateway, alerting).
- **[ASSIGNMENT_STAGE2.md](ASSIGNMENT_STAGE2.md)** — Stage 2: split across **two
  VMs** with **private-only** networking (gateway on its own VM, firewalled to the
  engine — the "IB Gateway on its own VM, private-IP to the engine" pattern).

> Dummy data only. `gateway_stub.py` imitates **IB Gateway's** flakiness
> (periodic re-auth outages + a token); `worker.py` imitates the stateful trading
> engine (persists ticks, heartbeat, retry/backoff).

## Components

| File | Role |
|---|---|
| `service/worker.py` | Stateful worker — polls gateway, persists ticks to SQLite, `/health` + `/status`, retry/backoff + reconnect counter |
| `service/gateway_stub.py` | Flaky **IB Gateway analog** — token-guarded, `reauth_required` 503 for ~10s/min |
| `service/db.py` | SQLite helper (DB on a persistent path) |
| `systemd/*.service` | Example units (adapt on the VM) |
| `tests/readiness_probe.py` | Liveness + persistence-through-outage check |

## Run locally (two terminals)

```bash
python -m venv .venv && . .venv/bin/activate       # Windows: .venv\Scripts\activate
pip install -r service/requirements.txt

# terminal 1 — the flaky gateway
GATEWAY_TOKEN=dev-gateway-token-change-me python service/gateway_stub.py

# terminal 2 — the worker (writes to ./data/service.db locally)
DB_PATH=./data/service.db GATEWAY_TOKEN=dev-gateway-token-change-me python service/worker.py
# open http://127.0.0.1:8070/status  and  /health
```

Check it:

```bash
BASE_URL=http://127.0.0.1:8070 python tests/readiness_probe.py
```

You'll see `tick_count` climbing and `reconnects` incrementing as the worker
rides the gateway's outage windows — that resilience is what you must keep alive
on the VM.
