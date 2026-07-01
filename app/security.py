"""Security middleware: API-key auth (constant-time), write-blocking, security
headers, and fail-closed error handling that never leaks stack traces."""

import hmac
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


def install_security(app):
    write_paths = app.config["WRITE_PATHS"]
    allowed_origins = set(app.config.get("CORS_ALLOWED_ORIGINS", []))

    @app.before_request
    def block_unlisted_writes():
        if request.method in ("POST", "PUT", "PATCH", "DELETE"):
            if request.path not in write_paths:
                return jsonify({"error": "read_only_endpoint"}), 403

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
