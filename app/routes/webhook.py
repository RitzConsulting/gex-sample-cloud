"""TradingView-style webhook intake. Validates + acknowledges only; it does not
write to the database in this sample. Left as a hardening exercise: add a shared
-secret check (see ASSIGNMENT.md)."""

from flask import Blueprint, jsonify, request

bp = Blueprint("webhook", __name__)


@bp.post("/webhook/tradingview")
def tradingview():
    payload = request.get_json(silent=True) or {}
    symbol = str(payload.get("symbol", ""))[:16].strip()
    if not symbol:
        return jsonify({"error": "missing_symbol"}), 400
    return jsonify({"status": "queued", "symbol": symbol})
