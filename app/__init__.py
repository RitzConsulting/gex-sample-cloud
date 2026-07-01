"""Application factory for the GEX sample cloud service."""

from flask import Flask

from .config import load_config, using_default_secrets
from .db import close_db, init_db
from .security import install_security
from .seed import seed_if_empty


def create_app(overrides=None):
    app = Flask(__name__)

    cfg = load_config()
    if overrides:
        cfg.update(overrides)
    app.config.update(cfg)
    app.secret_key = cfg["FLASK_SECRET_KEY"]
    app.teardown_appcontext(close_db)

    install_security(app)

    from .routes import api, dashboard, health, sync, webhook
    for module in (health, sync, webhook, api, dashboard):
        app.register_blueprint(module.bp)

    init_db(app)
    seed_if_empty(app)

    if using_default_secrets(cfg):
        app.logger.warning(
            "Running with DEFAULT dev secrets. Set SYNC_API_KEY and "
            "FLASK_SECRET_KEY via Secret Manager before deploying to production."
        )
    return app
