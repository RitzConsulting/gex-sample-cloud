"""Configuration for the GEX sample cloud service.

All real secrets come from the environment (Secret Manager in production).
The DEFAULT_* values exist only so the app runs out-of-the-box in local dev —
the provided security test suite asserts these defaults are REJECTED on the
deployed URL, which forces you to set strong secrets via Secret Manager.
"""

import os

# Intentionally weak, well-known dev values. NEVER use these in production.
DEFAULT_DEV_API_KEY = "dev-insecure-key-change-me"
DEFAULT_DEV_FLASK_SECRET = "dev-only-flask-secret-change-me"
DEFAULT_DEV_WEBHOOK_SECRET = "dev-webhook-secret-change-me"

# Only these paths may be written to (POST/PUT/PATCH/DELETE). Everything else
# is rejected by the write-blocking middleware — the public surface is read-only.
WRITE_PATHS = {"/api/sync/push", "/webhook/tradingview"}


def load_config():
    """Build the app config dict fresh from the current environment."""
    here = os.path.dirname(os.path.abspath(__file__))
    default_db = os.path.join(os.path.dirname(here), "data", "sample.db")
    return {
        "SYNC_API_KEY": os.environ.get("SYNC_API_KEY", DEFAULT_DEV_API_KEY),
        "FLASK_SECRET_KEY": os.environ.get("FLASK_SECRET_KEY", DEFAULT_DEV_FLASK_SECRET),
        "WEBHOOK_SECRET": os.environ.get("WEBHOOK_SECRET", DEFAULT_DEV_WEBHOOK_SECRET),
        "DB_PATH": os.environ.get("DB_PATH", default_db),
        "PORT": int(os.environ.get("PORT", "8080")),
        # Never enable in production — the security suite checks that tracebacks
        # are not leaked to clients.
        "DEBUG": os.environ.get("FLASK_DEBUG", "0") == "1",
        "WRITE_PATHS": WRITE_PATHS,
        # Per-IP request cap on the write endpoints (defense-in-depth against
        # API-key brute force). Edge rate limiting (Cloud Armor) is recommended
        # on top — see docs/HARDENING.md.
        "RATE_LIMIT_PER_MIN": int(os.environ.get("RATE_LIMIT_PER_MIN", "60")),
        # Empty = same-origin only. Do NOT set "*" in production.
        "CORS_ALLOWED_ORIGINS": [o for o in os.environ.get("CORS_ALLOWED_ORIGINS", "").split(",") if o],
    }


def using_default_secrets(cfg):
    return (cfg["SYNC_API_KEY"] == DEFAULT_DEV_API_KEY or
            cfg["FLASK_SECRET_KEY"] == DEFAULT_DEV_FLASK_SECRET or
            cfg["WEBHOOK_SECRET"] == DEFAULT_DEV_WEBHOOK_SECRET)
