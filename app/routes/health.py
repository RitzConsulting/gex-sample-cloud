from flask import Blueprint, jsonify

from ..db import get_db

bp = Blueprint("health", __name__)


@bp.get("/api/health")
@bp.get("/healthz")
def health():
    try:
        get_db().execute("SELECT 1")
        db_ok = True
    except Exception:
        db_ok = False
    return jsonify({"status": "ok" if db_ok else "degraded", "db_ok": db_ok})
