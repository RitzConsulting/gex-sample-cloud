"""Seed the DB with DUMMY, non-confidential GEX + trade data on first run.

Nothing here is real: prices, GEX values, strikes, and P/L are randomly
generated from a fixed seed for reproducibility. There are NO accounts,
credentials, or broker details anywhere in this project.
"""

import random
from datetime import datetime, timedelta, timezone

from .db import get_db


def seed_if_empty(app):
    with app.app_context():
        db = get_db()
        if db.execute("SELECT COUNT(*) FROM gex_snapshots").fetchone()[0]:
            return

        rng = random.Random(42)
        base = datetime(2026, 6, 30, 13, 30, tzinfo=timezone.utc)

        spx = 5900.0
        for i in range(60):
            ts = (base + timedelta(minutes=5 * i)).isoformat()
            spx += rng.uniform(-8, 8)
            net = rng.uniform(-3e9, 4e9)
            db.execute(
                "INSERT INTO gex_snapshots (ts, spx_price, net_gex, put_wall, call_wall, regime) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (ts, round(spx, 2), round(net, 0), round(spx - 40, 0), round(spx + 35, 0),
                 "positive" if net > 0 else "negative"),
            )

        strategies = ["Iron Condor", "Put Credit Spread", "Call Debit Spread", "Iron Fly"]
        statuses = ["open", "closed", "expired"]
        for i in range(40):
            ts = (base + timedelta(minutes=7 * i)).isoformat()
            short = round(spx + rng.uniform(-50, 50), 0)
            db.execute(
                "INSERT INTO trade_ideas (ts, strategy, short_strike, long_strike, credit, status) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (ts, rng.choice(strategies), short, short - 15,
                 round(rng.uniform(0.5, 3.5), 2), rng.choice(statuses)),
            )
        db.commit()
