import os
import sqlite3

DB_PATH = os.environ.get("DB_PATH", "/var/lib/gexvm/data/service.db")


def get_conn():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    conn = get_conn()
    conn.execute(
        "CREATE TABLE IF NOT EXISTS ticks (id INTEGER PRIMARY KEY, ts REAL, price REAL)"
    )
    conn.commit()
    conn.close()


def tick_count():
    conn = get_conn()
    try:
        return conn.execute("SELECT COUNT(*) FROM ticks").fetchone()[0]
    finally:
        conn.close()
