# Security acceptance criteria

The runnable **black-box security suite lives in a separate repo**,
`gex-sample-cloud-tests`, owned by QA. It is executed against your **deployed
Cloud Run URL** — you do not need it in this repo. This page documents exactly
what it checks so you can self-verify before submitting.

Your deployment must satisfy **all** of the following:

| Criterion | What it means |
|---|---|
| HTTPS only | The service is served over TLS (Cloud Run default). |
| Security headers | `Content-Security-Policy`, `Strict-Transport-Security` (HSTS), `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY` are present. |
| No framework banner | The `Server` header does not leak `Werkzeug`/`gunicorn`/`python` versions. |
| Debug off | Flask debugger disabled; no stack traces returned to clients. |
| Ingestion requires auth | `POST /api/sync/push` without a valid `X-Sync-Key` is rejected (401/403). |
| Dev key disabled | The built-in dev key (`dev-insecure-key-change-me`) does **not** authenticate in prod — you set a strong `SYNC_API_KEY` via Secret Manager. |
| Webhook requires a secret | `POST /webhook/tradingview` without the shared secret is rejected — no unauthenticated write path. |
| Webhook dev secret disabled | The built-in dev webhook secret does **not** authenticate in prod. |
| Read-only public surface | Writes to non-ingestion paths return 403. |
| No secret/debug leak | No response body contains secrets, config, SQL errors, or stack traces. |
| Rate limiting | Write endpoints are rate-limited (in-app per-IP; edge Cloud Armor recommended — see [HARDENING.md](docs/HARDENING.md)). |
| Injection-safe | Malicious table/column names never cause a 500. |
| No exposed files | `/.env`, `/config.py`, `/.git/config`, `/wsgi.py`, … are not served. |
| CORS locked down | `Access-Control-Allow-Origin` is never `*` and never reflects an arbitrary origin. |

The functional behaviour these depend on is already implemented in the app
(`app/security.py`) — your job is to **preserve it and close the deployment-side
gaps** (real secrets, TLS, least-privilege SA, debug off). See
[ASSIGNMENT.md](ASSIGNMENT.md).

QA runs, roughly:

```bash
# in the gex-sample-cloud-tests repo
BASE_URL=https://your-service-xyz.a.run.app pytest -v
```
