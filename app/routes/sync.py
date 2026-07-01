"""Authenticated data ingestion — the write surface that mirrors the real
system's /api/sync/push. Protected by the X-Sync-Key API key. Table/column
names come only from the SCHEMA allowlist, and every value is bound as a
parameter, so this endpoint is not SQL-injectable.
"""

from flask import Blueprint, jsonify, request

from ..db import SCHEMA, get_db
from ..security import require_api_key

bp = Blueprint("sync", __name__)

MAX_ROWS = 5000


@bp.post("/api/sync/push")
@require_api_key
def push():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "invalid_payload"}), 400

    table = data.get("table")
    rows = data.get("rows")
    if table not in SCHEMA:
        return jsonify({"error": "unknown_table"}), 400
    if not isinstance(rows, list) or not rows:
        return jsonify({"error": "no_rows"}), 400
    if len(rows) > MAX_ROWS:
        return jsonify({"error": "too_many_rows"}), 413

    cols = SCHEMA[table]  # allowlisted identifiers only
    col_list = ", ".join(f'"{c}"' for c in cols)
    placeholders = ", ".join(["?"] * len(cols))

    db = get_db()
    applied = 0
    for row in rows:
        if not isinstance(row, dict):
            continue
        values = [row.get(c) for c in cols]
        db.execute(
            f'INSERT INTO "{table}" ({col_list}) VALUES ({placeholders})', values
        )
        applied += 1
    db.commit()
    return jsonify({"status": "ok", "applied": applied})
