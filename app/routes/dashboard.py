from flask import Blueprint, render_template

from ..db import get_db

bp = Blueprint("dashboard", __name__)


@bp.get("/")
def index():
    db = get_db()
    gex = db.execute("SELECT * FROM gex_snapshots ORDER BY id DESC LIMIT 1").fetchone()
    ideas = db.execute("SELECT * FROM trade_ideas ORDER BY id DESC LIMIT 20").fetchall()
    return render_template("dashboard.html", gex=gex, ideas=ideas)
