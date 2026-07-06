# gex-sample-cloud

A small, self-contained Flask service that **mimics the cloud-facing surface of
a GEX options trading system** — a read-only dashboard backed by SQLite,
an authenticated data-ingestion endpoint, a webhook intake, and a health check.

It exists as a **take-home / training assignment** for the cloud-migration role.

## 👉 Candidates: what you're expected to do

Full brief in **[ASSIGNMENT.md](ASSIGNMENT.md)**. In short:

1. **Sign up for Google Cloud free tier** (<https://cloud.google.com/free>, ~$0
   for this exercise) and use **your own** project — you get no access to ours.
2. **Containerize** this app (write the `Dockerfile`) and **deploy it to Cloud
   Run** with reproducible automation (`cloudbuild.yaml` or `gcloud`).
3. **Secure the running service**: secrets via **Secret Manager**, HTTPS/HSTS,
   debug off, least-privilege service account, read-only public surface. You may
   (and are encouraged to) **add further tightening** — document it.
4. **Test it**: run the app locally, then run the black-box security suite
   ([`gex-sample-cloud-tests`](../gex-sample-cloud-tests)) against your live URL —
   all checks must pass. Criteria in **[SECURITY_TESTS.md](SECURITY_TESTS.md)**.
5. **Demonstrate**: share your live `*.run.app` URL, your deploy config, and a
   short `SUBMISSION.md` write-up.

**Round 2** (after Round 1 passes): **[ROUND2.md](ROUND2.md)** adds the
production-shaped work — durable **persistence across deploys**, auto-deploy with
immutable tags, rollback, edge WAF (Cloud Armor), and observability.

**VM readiness (Path A):** **[vm-exercise/](vm-exercise/)** rehearses a single
hardened GCE VM running a **stateful worker** + a **flaky IB-Gateway-analog** —
`systemd` supervision, a persistent disk that survives reboot, Secret Manager,
firewall/TLS, and a "gateway down too long" alert.

> ⚠️ Everything here is **dummy data**. There are no real accounts, credentials,
> broker integrations, or trading logic. Prices, GEX values, and trades are
> randomly generated. Nothing confidential is included.

## What it represents (and what it deliberately omits)

| Included (representative) | Omitted (not needed to test cloud security) |
|---|---|
| Flask app + read-only dashboard | Real strategy / GEX math |
| SQLite storage + seed data | Broker execution (live brokers) |
| Authenticated sync ingestion (`/api/sync/push`) | Real account creation / credentials |
| Webhook intake (`/webhook/tradingview`) | The full multi-strategy scheduler |
| Health check, write-blocking, security headers | Cloud sync worker internals |
| Secrets via environment (Secret Manager in prod) | — |

## Architecture

![architecture](docs/architecture.png)

```
client / TradingView ──▶  Flask service (this repo)  ──▶  SQLite (dummy data)
                          - GET  /                       dashboard (read-only)
                          - GET  /api/gex/latest         JSON
                          - GET  /api/trade-ideas        JSON
                          - GET  /api/health             health
                          - POST /api/sync/push          INGEST (X-Sync-Key)
                          - POST /webhook/tradingview    webhook intake
   Secret Manager  ──▶    SYNC_API_KEY, FLASK_SECRET_KEY (env)
```

## Run locally

**Quickest (one command):**
- Windows: double-click **`start.cmd`** (or `./start.ps1`)
- macOS/Linux: **`./start.sh`**

It creates a virtualenv, installs deps, starts the app, and opens the dashboard
at http://127.0.0.1:8080. Run the tests with `test.ps1` (Windows) or `pytest`.

**Manual:**

```bash
python -m venv .venv && . .venv/bin/activate      # (Windows: .venv\Scripts\activate)
pip install -r requirements-dev.txt
cp .env.example .env                              # optional; dev defaults work
python run.py                                     # http://127.0.0.1:8080
```

Try it:

```bash
curl http://127.0.0.1:8080/api/health
curl http://127.0.0.1:8080/api/gex/latest
# authenticated ingest (dev key):
curl -X POST http://127.0.0.1:8080/api/sync/push \
  -H "X-Sync-Key: dev-insecure-key-change-me" -H "Content-Type: application/json" \
  -d '{"table":"trade_ideas","rows":[{"ts":"2026-06-30T14:00:00","strategy":"Iron Condor","short_strike":5900,"long_strike":5885,"credit":1.2,"status":"open"}]}'
```

## Tests

```bash
pytest                                            # functional / in-app tests (no network)
```

The **black-box security suite lives in a separate repo** — `gex-sample-cloud-tests`
— and is run by QA against your **deployed URL** (`BASE_URL=… pytest`). You don't
run it from here. The acceptance criteria (exactly what "secure" is checked for)
are documented in **[SECURITY_TESTS.md](SECURITY_TESTS.md)** so there are no
surprises.

## Security posture (already built in)

Parameterized SQL only · API-key auth with constant-time compare · write-blocking
middleware (only `/api/sync/push` + `/webhook/tradingview` are writable) ·
security headers (CSP, HSTS, `nosniff`, `DENY` framing) · fail-closed error
handling (no stack traces) · secrets from env · non-wildcard CORS · loopback-only
dev server. Your job is to **keep this posture intact while deploying to GCP**
and to close the deployment-side gaps (secrets, TLS, least-privilege, etc).
