import pytest


@pytest.fixture()
def app(tmp_path, monkeypatch):
    # Isolated temp DB; default dev secrets (functional tests use the dev key).
    monkeypatch.setenv("DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.delenv("SYNC_API_KEY", raising=False)
    monkeypatch.delenv("FLASK_SECRET_KEY", raising=False)
    monkeypatch.delenv("FLASK_DEBUG", raising=False)
    from app import create_app

    application = create_app()
    application.testing = True
    yield application


@pytest.fixture()
def client(app):
    return app.test_client()
