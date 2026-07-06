"""Functional + in-app security tests. Run with: pytest (uses the Flask test
client, no network needed). These always run in CI."""

from app.config import DEFAULT_DEV_API_KEY, DEFAULT_DEV_WEBHOOK_SECRET


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.get_json()["status"] == "ok"


def test_dashboard_renders(client):
    r = client.get("/")
    assert r.status_code == 200
    assert b"GEX Sample" in r.data


def test_gex_api_returns_data(client):
    r = client.get("/api/gex/latest")
    assert r.status_code == 200
    body = r.get_json()
    assert isinstance(body, list) and len(body) > 0


def test_security_headers(client):
    r = client.get("/api/health")
    assert r.headers.get("X-Content-Type-Options") == "nosniff"
    assert r.headers.get("X-Frame-Options") == "DENY"
    assert "Strict-Transport-Security" in r.headers
    assert "Content-Security-Policy" in r.headers


def test_sync_requires_key(client):
    r = client.post("/api/sync/push", json={"table": "gex_snapshots", "rows": [{}]})
    assert r.status_code == 401


def test_sync_rejects_wrong_key(client):
    r = client.post(
        "/api/sync/push",
        headers={"X-Sync-Key": "wrong"},
        json={"table": "gex_snapshots", "rows": [{}]},
    )
    assert r.status_code == 401


def test_sync_accepts_valid_key(client):
    payload = {
        "table": "trade_ideas",
        "rows": [{
            "ts": "2026-06-30T14:00:00", "strategy": "Iron Condor",
            "short_strike": 5900, "long_strike": 5885, "credit": 1.2, "status": "open",
        }],
    }
    r = client.post("/api/sync/push", headers={"X-Sync-Key": DEFAULT_DEV_API_KEY}, json=payload)
    assert r.status_code == 200
    assert r.get_json()["applied"] == 1


def test_sync_unknown_table_rejected(client):
    r = client.post(
        "/api/sync/push",
        headers={"X-Sync-Key": DEFAULT_DEV_API_KEY},
        json={"table": "users; DROP TABLE trade_ideas", "rows": [{}]},
    )
    assert r.status_code == 400


def test_write_blocking(client):
    assert client.post("/api/gex/latest", json={}).status_code == 403
    assert client.delete("/api/trade-ideas").status_code == 403
    assert client.put("/", json={}).status_code == 403


def test_sql_injection_param_is_safe(client):
    r = client.get("/api/trade-ideas", query_string={"status": "open' OR '1'='1"})
    assert r.status_code == 200
    # Parameterized query treats it as a literal → matches nothing.
    assert r.get_json() == []


def test_webhook_requires_secret(client):
    # No secret / wrong secret → 401 (no unauthenticated write path).
    assert client.post("/webhook/tradingview", json={"symbol": "SPX"}).status_code == 401
    assert client.post(
        "/webhook/tradingview", headers={"X-Webhook-Secret": "nope"}, json={"symbol": "SPX"}
    ).status_code == 401


def test_webhook_accepts_valid_secret(client):
    h = {"X-Webhook-Secret": DEFAULT_DEV_WEBHOOK_SECRET}
    assert client.post("/webhook/tradingview", headers=h, json={}).status_code == 400  # missing symbol
    assert client.post("/webhook/tradingview", headers=h, json={"symbol": "SPX"}).status_code == 200
    # Secret in the JSON body is also accepted.
    assert client.post(
        "/webhook/tradingview", json={"secret": DEFAULT_DEV_WEBHOOK_SECRET, "symbol": "SPX"}
    ).status_code == 200


def test_rate_limiting_on_writes(tmp_path, monkeypatch):
    monkeypatch.setenv("DB_PATH", str(tmp_path / "rl.db"))
    from app import create_app
    from app.security import _limiter

    _limiter._hits.clear()  # isolate from other tests' write requests
    app = create_app({"RATE_LIMIT_PER_MIN": 3})
    c = app.test_client()
    codes = [c.post("/api/sync/push", json={}).status_code for _ in range(6)]
    assert 429 in codes  # limiter trips before auth is even checked


def test_no_secret_leak_in_bodies(client):
    markers = [
        "dev-insecure-key-change-me", "dev-only-flask-secret-change-me",
        "dev-webhook-secret-change-me", "SYNC_API_KEY", "FLASK_SECRET_KEY",
        "Traceback (most recent call last)", "sqlite3.",
    ]
    bodies = [client.get(p).get_data(as_text=True)
              for p in ["/", "/api/health", "/api/gex/latest", "/api/trade-ideas", "/nope-xyz"]]
    bodies.append(client.post(
        "/api/sync/push", headers={"X-Sync-Key": DEFAULT_DEV_API_KEY},
        json={"table": "'; DROP TABLE x;--", "rows": [{}]},
    ).get_data(as_text=True))
    blob = "\n".join(bodies)
    for m in markers:
        assert m not in blob


# Broader injection coverage (merged from candidate review): values that would
# be dangerous if ever string-formatted into SQL must be inert and never 500.
INJECTION_PAYLOADS = [
    "' OR 1=1 --",
    "'; DROP TABLE trade_ideas; --",
    "' UNION SELECT NULL,NULL --",
    "admin'--",
]


def test_injection_payloads_are_inert(client):
    for p in INJECTION_PAYLOADS:
        r = client.post(
            "/api/sync/push", headers={"X-Sync-Key": DEFAULT_DEV_API_KEY},
            json={"table": "trade_ideas", "rows": [{
                "ts": "t", "strategy": p, "short_strike": 1,
                "long_strike": 2, "credit": 1, "status": "open"}]},
        )
        assert r.status_code == 200  # stored as a literal, no injection
    # The table survived and the API still works.
    assert client.get("/api/trade-ideas").status_code == 200


def test_dashboard_escapes_xss(client):
    xss = "<script>alert(1)</script>"
    client.post(
        "/api/sync/push", headers={"X-Sync-Key": DEFAULT_DEV_API_KEY},
        json={"table": "trade_ideas", "rows": [{
            "ts": "2026-01-01", "strategy": xss, "short_strike": 1,
            "long_strike": 2, "credit": 1, "status": "open"}]},
    )
    html = client.get("/").get_data(as_text=True)
    assert xss not in html            # never rendered raw
    assert "&lt;script&gt;" in html   # HTML-escaped on output
