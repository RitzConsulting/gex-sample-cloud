"""Flaky 'broker gateway' — stands in for IB Gateway.

Deliberately mimics IB Gateway's real-world pain: it periodically returns
'reauth_required' (503) for ~10s of every minute, and requires a token. The
candidate must run it under a supervisor (systemd Restart=always) and prove the
worker rides through the outages + that alerts fire on a *prolonged* outage.

Run: GATEWAY_TOKEN=... python gateway_stub.py   (default port 8071)
"""

import math
import os
import time

from flask import Flask, abort, jsonify, request

TOKEN = os.environ.get("GATEWAY_TOKEN", "dev-gateway-token-change-me")
PORT = int(os.environ.get("GATEWAY_PORT", "8071"))
# Stage 1 (single VM): keep 127.0.0.1. Stage 2 (two VMs): set GATEWAY_HOST=0.0.0.0
# so the engine VM reaches it over the PRIVATE VPC IP — and rely on a VPC firewall
# that allows ONLY the engine VM. Never open this port to 0.0.0.0/0.
HOST = os.environ.get("GATEWAY_HOST", "127.0.0.1")

app = Flask(__name__)
_start = time.time()


@app.get("/tick")
def tick():
    if request.headers.get("X-Gateway-Token") != TOKEN:
        abort(401)
    t = time.time() - _start
    # ~10s reauth window out of every 60s (like IB's session drops).
    if int(t) % 60 < 10:
        return jsonify({"error": "reauth_required"}), 503
    return jsonify({"price": round(6000 + 20 * math.sin(t / 5.0), 2), "ts": time.time()})


@app.get("/health")
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    app.run(host=HOST, port=PORT)
