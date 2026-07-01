"""TradingView-style webhook intake. Requires a shared secret (via the
`X-Webhook-Secret` header or a `secret` field in the JSON body), then validates
and acknowledges. It does not write to the database in this sample."""

from flask import Blueprint, jsonify, request

from ..security import require_webhook_secret

bp = Blueprint("webhook", __name__)


@bp.post("/webhook/tradingview")
@require_webhook_secret
def tradingview():
    payload = request.get_json(silent=True) or {}
    symbol = str(payload.get("symbol", ""))[:16].strip()
    if not symbol:
        return jsonify({"error": "missing_symbol"}), 400
    return jsonify({"status": "queued", "symbol": symbol})
