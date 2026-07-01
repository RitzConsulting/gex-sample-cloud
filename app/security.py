"""Security middleware: API-key auth (constant-time), write-blocking, security
headers, and fail-closed error handling that never leaks stack traces."""

import hmac
import threading
import time
from functools import wraps

from flask import current_app, jsonify, request
from werkzeug.exceptions import HTTPException


def valid_api_key(provided):
    if not provided:
        return False
    configured = current_app.config["SYNC_API_KEY"]
    # Constant-time compare to avoid timing side-channels.
    return hmac.compare_digest(str(provided), str(configured))


def require_api_key(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not valid_api_key(request.headers.get("X-Sync-Key", "")):
            return jsonify({"error": "unauthorized"}), 401
        return fn(*args, **kwargs)

    return wrapper


def valid_webhook_secret(provided):
    if not provided:
        return False
    configured = current_app.config["WEBHOOK_SECRET"]
    return hmac.compare_digest(str(provided), str(configured))


def require_webhook_secret(fn):
    """Webhook auth: shared secret via the `X-Webhook-Secret` header, or a
    `secret` field in the JSON body (some senders can't set headers)."""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        provided = request.headers.get("X-Webhook-Secret")
        if not provided:
            provided = (request.get_json(silent=True) or {}).get("secret", "")
        if not valid_webhook_secret(provided):
            return jsonify({"error": "unauthorized"}), 401
        return fn(*args, **kwargs)

    return wrapper


class _RateLimiter:
    """Tiny per-key fixed-window limiter (in-memory, per instance). Defense in
    depth only — put Cloud Armor in front for real edge rate limiting."""

    def __init__(self):
        self._hits = {}
        self._lock = threading.Lock()

    def allow(self, key, limit, window=60.0):
        now = time.time()
        with self._lock:
            start, count = self._hits.get(key, (now, 0))
            if now - start >= window:
                start, count = now, 0
            count += 1
            self._hits[key] = (start, count)
            return count <= limit


_limiter = _RateLimiter()


def _client_ip():
    xff = request.headers.get("X-Forwarded-For", "")
    if xff:
        return xff.split(",")[0].strip()
    return request.remote_addr or "unknown"


def install_security(app):
    write_paths = app.config["WRITE_PATHS"]
    allowed_origins = set(app.config.get("CORS_ALLOWED_ORIGINS", []))

    @app.before_request
    def block_unlisted_writes():
        if request.method in ("POST", "PUT", "PATCH", "DELETE"):
            if request.path not in write_paths:
                return jsonify({"error": "read_only_endpoint"}), 403

    @app.before_request
    def rate_limit_writes():
        # Cap requests to the write endpoints per client IP (runs before auth,
        # so it also throttles API-key brute force).
        if request.path in write_paths:
            limit = app.config.get("RATE_LIMIT_PER_MIN", 60)
            if not _limiter.allow(_client_ip(), limit):
                return jsonify({"error": "rate_limited"}), 429

    @app.after_request
    def security_headers(resp):
        resp.headers["X-Content-Type-Options"] = "nosniff"
        resp.headers["X-Frame-Options"] = "DENY"
        resp.headers["Referrer-Policy"] = "no-referrer"
        resp.headers["Content-Security-Policy"] = (
            "default-src 'self'; style-src 'self' 'unsafe-inline'; "
            "base-uri 'none'; frame-ancestors 'none'; object-src 'none'"
        )
        resp.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        # Safe to always send; browsers only honour it over HTTPS.
        resp.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        # Never leak the framework/version banner.
        resp.headers["Server"] = "gex-sample"
        # Explicit, non-wildcard CORS (only echo allowlisted origins).
        origin = request.headers.get("Origin")
        if origin and origin in allowed_origins:
            resp.headers["Access-Control-Allow-Origin"] = origin
            resp.headers["Vary"] = "Origin"
        return resp

    @app.errorhandler(Exception)
    def handle_error(e):
        if isinstance(e, HTTPException):
            return jsonify({"error": e.name.lower().replace(" ", "_")}), e.code
        app.logger.exception("unhandled error")
        # Generic message only — never expose the exception/traceback.
        return jsonify({"error": "internal_error"}), 500
