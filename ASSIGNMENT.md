# Assignment — Secure Cloud Migration of the GEX Sample Service

## Context

This repository is a slimmed-down stand-in for the cloud-facing part of our GEX
trading platform. The application code is written to a reasonable security
baseline **on purpose** — your task is **not** to find bugs in the app, but to
**containerize it, deploy it to Google Cloud, and make the running service
secure**, then prove it by passing the provided security test suite.

Everything in the repo is dummy data. No confidential information is included,
and none should be added.

## Your goal

Deploy this service to **Google Cloud Run** such that QA's black-box security
suite (a **separate repo, `gex-sample-cloud-tests`**) passes **100%** against
your live URL, and the deployment follows least-privilege, secrets-managed,
HTTPS-only practices. The exact acceptance criteria are in
[SECURITY_TESTS.md](SECURITY_TESTS.md) — nothing is hidden.

## What you must deliver

1. **Containerization** — a `Dockerfile` that runs the app under a production
   WSGI server (gunicorn, `wsgi:app`) binding `0.0.0.0:$PORT`. (There is
   intentionally no Dockerfile in the repo — writing it is part of the task.)
2. **Deployment automation** — a `cloudbuild.yaml` **or** a documented set of
   `gcloud` commands that build + deploy the service. Reproducible, not click-ops.
3. **Secret management** — `SYNC_API_KEY` and `FLASK_SECRET_KEY` supplied from
   **Secret Manager** (not baked into the image, not committed, not the built-in
   dev defaults). The suite verifies the dev key does **not** work in prod.
4. **Runtime hardening**
   - HTTPS only; HSTS present (already emitted by the app — keep it).
   - `FLASK_DEBUG` must be off (no stack traces to clients).
   - Least-privilege **runtime service account** (no `Editor`/`Owner`; grant only
     what the service needs — e.g. Secret Manager accessor for its own secrets).
   - Public dashboard is fine (`--allow-unauthenticated`), but the **ingestion**
     endpoint must remain API-key protected.
   - Sensible resource limits and a low max-instance count.
5. **A short write-up** (`SUBMISSION.md`) covering: your architecture choices,
   the exact deploy steps, how secrets are handled, the least-privilege SA, and
   your **live URL** plus evidence you meet the criteria in
   [SECURITY_TESTS.md](SECURITY_TESTS.md) (e.g. `curl -I` output).

## What we will do to evaluate

- Run the separate `gex-sample-cloud-tests` suite against your URL and confirm
  **all tests pass**.
- Review your `Dockerfile`, deploy config, and IAM for least privilege.
- Probe the URL manually (headers, auth, error handling, exposed paths).
- Confirm no secrets are committed and the dev key is disabled in prod.

## Guardrails

- **Don't weaken the app to pass tests.** You may *strengthen* it (e.g. add
  webhook auth, rate limiting) — document anything you change.
- Don't add real credentials or real data.
- Keep the public dashboard read-only; don't open new write paths.

See [docs/HARDENING.md](docs/HARDENING.md) for concrete secret / least-privilege
/ Cloud Armor examples.

## Stretch goals (optional, called out in your write-up)

- **Edge** rate limiting / WAF (Cloud Armor) in front of the service (the app
  already has a per-instance limiter; the edge one is the real protection).
- Structured request logging + a log-based alert on repeated `401/403/429`.
- CI that runs `pytest` on push and blocks deploy on failure.
- Cloud Run **min-instances** + startup DB restore if you persist SQLite.

## Time

Aim for **4–8 hours**. We care about correctness, security posture, and clear
reproducible automation — not feature volume.
