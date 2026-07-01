# Security test suite

Two layers:

- **`tests/test_functional.py`** — runs against the Flask test client (no
  network). Verifies the app's built-in security behaviour (auth, write-blocking,
  headers, parameterized SQL). Runs on every `pytest`.
- **`tests/test_security.py`** — runs against the **deployed URL**. Skipped
  unless `BASE_URL` is set. This is what the evaluator runs to confirm the live
  service is secure.

## Run against a deployed service

```bash
pip install -r requirements-dev.txt
BASE_URL=https://your-service-xyz-uc.a.run.app pytest tests/test_security.py -v
```

All tests must pass.

## What the remote suite checks

| Test | Why it matters |
|---|---|
| `test_uses_https` | Service is HTTPS-only |
| `test_security_headers_present` | CSP, HSTS, `nosniff`, `X-Frame-Options: DENY` |
| `test_no_framework_banner` | No `Werkzeug`/`gunicorn`/`python` version leak in `Server` |
| `test_debug_off_no_traceback` | Flask debugger off; no stack traces to clients |
| `test_sync_requires_key` | Ingestion rejects unauthenticated writes |
| `test_default_dev_key_is_rejected` | Real secret set via Secret Manager (dev key disabled) |
| `test_write_blocking_on_read_endpoints` | Public surface is read-only |
| `test_injection_never_500s` | Malicious table/column names never cause a 500 |
| `test_no_secret_or_source_files_served` | `/.env`, `/config.py`, `/.git/config`, … not served |
| `test_cors_not_wildcard_or_reflected` | CORS not `*` and doesn't reflect arbitrary origins |

## Notes

- The suite is intentionally **black-box** — it only needs your URL.
- A green run is necessary but not sufficient: we also review your IAM, container,
  and deploy automation. See [ASSIGNMENT.md](ASSIGNMENT.md).
