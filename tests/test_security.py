"""Remote security suite — run against the DEPLOYED Cloud Run URL.

    BASE_URL=https://your-service-xyz.a.run.app pytest tests/test_security.py

The whole module is skipped unless BASE_URL is set, so `pytest` alone (CI) runs
only the functional tests. This is the suite the evaluator runs to confirm the
deployed service is secure.
"""

import os

import pytest
import requests

BASE_URL = os.environ.get("BASE_URL", "").rstrip("/")
DEV_KEY = "dev-insecure-key-change-me"
TIMEOUT = 15

pytestmark = pytest.mark.skipif(
    not BASE_URL,
    reason="Set BASE_URL to the deployed Cloud Run URL to run the remote security suite",
)


def u(path):
    return f"{BASE_URL}{path}"


def test_uses_https():
    assert BASE_URL.startswith("https://"), "Deployed URL must be served over HTTPS"


def test_health_reachable():
    assert requests.get(u("/api/health"), timeout=TIMEOUT).status_code == 200


def test_security_headers_present():
    h = requests.get(u("/api/health"), timeout=TIMEOUT).headers
    assert h.get("X-Content-Type-Options") == "nosniff"
    assert h.get("X-Frame-Options") == "DENY"
    assert "Strict-Transport-Security" in h, "HSTS header missing"
    assert "Content-Security-Policy" in h, "CSP header missing"


def test_no_framework_banner():
    server = requests.get(u("/api/health"), timeout=TIMEOUT).headers.get("Server", "").lower()
    assert "werkzeug" not in server
    assert "gunicorn" not in server
    assert "python" not in server


def test_debug_off_no_traceback():
    r = requests.get(u("/no-such-route-abc123"), timeout=TIMEOUT)
    assert r.status_code in (403, 404)
    body = r.text.lower()
    assert "traceback" not in body
    assert "werkzeug" not in body  # interactive debugger must be disabled


def test_sync_requires_key():
    r = requests.post(u("/api/sync/push"), json={"table": "gex_snapshots", "rows": [{}]}, timeout=TIMEOUT)
    assert r.status_code in (401, 403)


def test_default_dev_key_is_rejected():
    """The candidate MUST configure a strong SYNC_API_KEY via Secret Manager;
    the built-in dev key must never authenticate in production."""
    r = requests.post(
        u("/api/sync/push"),
        headers={"X-Sync-Key": DEV_KEY},
        json={"table": "gex_snapshots", "rows": [{"ts": "x"}]},
        timeout=TIMEOUT,
    )
    assert r.status_code in (401, 403), "Default dev API key must NOT work in production"


def test_write_blocking_on_read_endpoints():
    assert requests.post(u("/api/gex/latest"), json={}, timeout=TIMEOUT).status_code == 403


def test_injection_never_500s():
    r = requests.post(
        u("/api/sync/push"),
        headers={"X-Sync-Key": DEV_KEY},
        json={"table": "x; DROP TABLE gex_snapshots;--", "rows": [{}]},
        timeout=TIMEOUT,
    )
    assert r.status_code in (400, 401, 403)
    assert r.status_code != 500


def test_no_secret_or_source_files_served():
    for path in ["/.env", "/config.py", "/app/config.py", "/.git/config", "/wsgi.py"]:
        code = requests.get(u(path), timeout=TIMEOUT).status_code
        assert code in (403, 404), f"{path} must not be served (got {code})"


def test_cors_not_wildcard_or_reflected():
    r = requests.get(u("/api/health"), headers={"Origin": "https://evil.example"}, timeout=TIMEOUT)
    acao = r.headers.get("Access-Control-Allow-Origin")
    assert acao != "*"
    assert acao != "https://evil.example"
