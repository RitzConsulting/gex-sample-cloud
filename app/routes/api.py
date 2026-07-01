"""Read-only JSON APIs backing the dashboard. All queries are parameterized."""

from flask import Blueprint, jsonify, request

from ..db import get_db

bp = Blueprint("api", __name__)


@bp.get("/api/gex/latest")
def gex_latest():
    rows = get_db().execute(
        "SELECT * FROM gex_snapshots ORDER BY id DESC LIMIT 50"
    ).fetchall()
    return jsonify([dict(r) for r in rows])


@bp.get("/api/trade-ideas")
def trade_ideas():
    status = request.args.get("status")
    db = get_db()
    if status:
        rows = db.execute(
            "SELECT * FROM trade_ideas WHERE status = ? ORDER BY id DESC LIMIT 100",
            (status,),
        ).fetchall()
    else:
        rows = db.execute(
            "SELECT * FROM trade_ideas ORDER BY id DESC LIMIT 100"
        ).fetchall()
    return jsonify([dict(r) for r in rows])
