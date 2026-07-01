"""SQLite access + schema. All queries are parameterized; the only table/column
names ever interpolated into SQL come from the ALLOWLIST below."""

import os
import re
import sqlite3

from flask import current_app, g

_IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,63}$")

# Ingestion allowlist — the sync endpoint will only write these tables/columns.
# Any table/column not listed here is rejected before touching SQL.
SCHEMA = {
    "gex_snapshots": ["ts", "spx_price", "net_gex", "put_wall", "call_wall", "regime"],
    "trade_ideas": ["ts", "strategy", "short_strike", "long_strike", "credit", "status"],
}


def get_db():
    if "db" not in g:
        path = current_app.config["DB_PATH"]
        os.makedirs(os.path.dirname(path), exist_ok=True)
        g.db = sqlite3.connect(path)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA journal_mode=WAL")
    return g.db


def close_db(_e=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db(app):
    with app.app_context():
        db = get_db()
        db.execute(
            """CREATE TABLE IF NOT EXISTS gex_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts TEXT, spx_price REAL, net_gex REAL,
                put_wall REAL, call_wall REAL, regime TEXT)"""
        )
        db.execute(
            """CREATE TABLE IF NOT EXISTS trade_ideas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts TEXT, strategy TEXT, short_strike REAL,
                long_strike REAL, credit REAL, status TEXT)"""
        )
        db.commit()


def valid_ident(name):
    return bool(isinstance(name, str) and _IDENT.match(name))
