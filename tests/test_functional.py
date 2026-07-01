"""Functional + in-app security tests. Run with: pytest (uses the Flask test
client, no network needed). These always run in CI."""

from app.config import DEFAULT_DEV_API_KEY


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


def test_webhook_validates_input(client):
    assert client.post("/webhook/tradingview", json={}).status_code == 400
    assert client.post("/webhook/tradingview", json={"symbol": "SPX"}).status_code == 200
