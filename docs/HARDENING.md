# Deployment hardening notes

The app ships secure-by-default (auth, write-blocking, parameterized SQL,
security headers, fail-closed errors, in-app per-IP rate limiting). These are the
**cloud-side** controls you own when deploying.

## Secrets

- Put `SYNC_API_KEY`, `FLASK_SECRET_KEY`, and `WEBHOOK_SECRET` in **Secret
  Manager**; inject them as env at deploy. Never bake them into the image, commit
  them, or echo them in logs.
- Rotate by adding a new secret version and redeploying.
- The built-in `dev-*-change-me` values must never reach production — the suite
  fails if they still authenticate.

## Least-privilege runtime service account

Don't run the service as the default Compute SA with broad roles. Create a
dedicated SA and grant only what it needs:

```bash
gcloud iam service-accounts create gex-sample-run
# access ONLY its own secrets:
for S in SYNC_API_KEY FLASK_SECRET_KEY WEBHOOK_SECRET; do
  gcloud secrets add-iam-policy-binding $S \
    --member="serviceAccount:gex-sample-run@$PROJECT.iam.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor"
done
gcloud run deploy gex-sample-cloud --service-account gex-sample-run@$PROJECT.iam.gserviceaccount.com ...
```

No `Editor`/`Owner`. No project-wide `secretAccessor`.

## Rate limiting

The app has a small in-memory per-IP cap (`RATE_LIMIT_PER_MIN`, default 60) on
the write endpoints — defense in depth against API-key brute force. It is
per-instance, so put **edge** rate limiting in front for real protection.

Cloud Armor rate-based ban (example):

```bash
gcloud compute security-policies create gex-sample-policy
gcloud compute security-policies rules create 1000 \
  --security-policy gex-sample-policy \
  --expression "true" \
  --action rate-based-ban \
  --rate-limit-threshold-count 100 \
  --rate-limit-threshold-interval-sec 60 \
  --ban-duration-sec 300 \
  --conform-action allow --exceed-action deny-429 \
  --enforce-on-key IP
```

Attach the policy to the backend fronting Cloud Run (via an external HTTPS load
balancer + serverless NEG).

## Other

- `FLASK_DEBUG` off (no interactive debugger / tracebacks).
- Keep the public dashboard read-only; don't add write paths.
- Structured request logging, but **never** log secret headers/bodies.
- Consider a log-based alert on repeated `401/403/429`.
- If you persist SQLite, use a private GCS bucket (no public access) and rely on
  Google-managed encryption at rest.
