# Round 2 — Operational Hardening & Stateful Persistence

## Where you landed in Round 1

Your Round 1 submission **passed all 14 security checks against your live Cloud
Run URL** (independently re-verified), with a correct least-privilege runtime
service account, Secret Manager for all secrets, a clean non-root Docker image,
and Cloud Build automation — and you didn't weaken the app to pass. Excellent
work, well above the bar. You also added CI, API tests, a security scanner, and
load tests on your own initiative.

Round 2 builds directly on that. It closes a few refinements and — most
importantly — makes the service **stateful and operationally production-ready**,
which is the real shape of the migration you'd be taking over. The production
service must **keep its data across deploys**, deploy **automatically** with
**rollbackable** revisions, and be **observable**. That's what Round 2 tests.

---

## Scope (what to add)

### 1. Data persistence across deploys  ⭐ (the headline)

Today the SQLite database lives on Cloud Run's **ephemeral, in-memory
filesystem** — every redeploy or cold start **wipes all ingested data**. In the
real system the cloud must retain data across deploys. Fix this.

Pick **one** approach and justify it:
- **A — GCS-backed SQLite:** restore the DB file from a GCS bucket on startup,
  and snapshot it back periodically / on shutdown (use the SQLite backup API for
  a consistent copy). Requires a single writer — pin `--max-instances=1`.
- **B — Cloud SQL (Postgres):** run a small Cloud SQL instance, point the app at
  it via a connection string from Secret Manager, and connect through the Cloud
  SQL Auth Proxy / Cloud Run's built-in connector. Multi-instance safe.

**Acceptance:** a record ingested via `POST /api/sync/push` is **still returned
by `GET /api/trade-ideas` after the service is redeployed** (new revision / cold
start). We verify this with `round2/persistence_probe.py` in the tests repo
(seed → you redeploy → verify).

> Note which trade-offs drove your choice (cost, concurrency, complexity,
> single-writer constraint). There's no single right answer — the reasoning matters.

### 2. Automated deploys + immutable image tags

- Wire **deploy-on-merge to `main`** (a Cloud Build trigger, or GitHub Actions →
  Cloud Run). No more manual `gcloud builds submit`.
- Tag images by **commit SHA** (immutable), not `:latest`, so every revision is
  traceable and rollbackable.

**Acceptance:** a commit to `main` produces a new Cloud Run revision whose image
is tagged with that commit SHA.

### 3. Rollback & zero-downtime

- Show you can **roll back** to a previous revision and split/shift traffic.

**Acceptance:** document (and ideally script) a rollback, e.g.
`gcloud run services update-traffic gex-sample-cloud --to-revisions <prev>=100`,
and note how you'd do a canary (e.g. 10% → 100%).

### 4. Edge protection (Cloud Armor / WAF)

- Front the service with an **external HTTPS Load Balancer + serverless NEG** and
  attach a **Cloud Armor** policy with a rate-based ban rule (the in-app limiter
  is per-instance defense-in-depth only). If you choose not to build the LB,
  provide the full IaC/commands and explain the design.

**Acceptance:** edge rate limiting is enforced (or a complete, scripted setup +
rationale). See `docs/HARDENING.md` for a starting example.

### 5. Observability

- **Structured logging** (JSON) without secrets.
- A **log-based metric + alert** on repeated `401/403/429` and any `5xx`.
- An **uptime check** on `/api/health`.

**Acceptance:** alert policy + uptime check exist (screenshots or IaC), and logs
are structured.

### 6. Dockerfile polish

- Honor Cloud Run's injected port: bind `0.0.0.0:${PORT:-8080}` instead of a
  hardcoded `8080`.
- Pin the base image by **digest** (`python:3.11-slim@sha256:...`) for
  reproducibility, and add a container `HEALTHCHECK`.

### 7. Output-escaping / XSS verification

- Extend your scanner (or add a test) to **fetch the rendered dashboard** after
  ingesting an XSS payload and assert it is **HTML-escaped on output** (not just
  that the write returned non-500). Confirm the app's autoescaping holds.

---

## How we'll re-test

1. **Persistence (automated):** we run `round2/persistence_probe.py seed` with a
   marker → **you redeploy** → we run `... verify` and confirm the marker
   survived. (See the tests repo `round2/README.md`.)
2. **Security regression:** the full 14-check suite must **still pass** on the new
   (stateful, LB-fronted) deployment.
3. **Review:** we inspect your CI/CD trigger, SHA tagging, rollback doc, Cloud
   Armor policy, and monitoring (alerts + uptime check).

---

## Deliverables

- Updated deployment (persistence + auto-deploy + edge + observability).
- `ROUND2_SUBMISSION.md`: your persistence choice + rationale, the CI/CD + tagging
  setup, a rollback runbook, the Cloud Armor/LB design, and monitoring evidence
  (screenshots / IaC). Include your **live URL** (LB URL if applicable).
- Keep everything reproducible (IaC / documented commands), and **don't modify
  the application's security behavior** to pass — strengthen only, and document it.

## Time

Aim for **6–10 hours**. Persistence (#1) is the priority — if you're short on
time, do #1, #2, and #6 well and outline the rest.
