"""Local dev runner. Binds loopback only — do NOT use this to serve production;
use gunicorn with wsgi:app in your container (see ASSIGNMENT.md)."""

from app import create_app

if __name__ == "__main__":
    app = create_app()
    app.run(host="127.0.0.1", port=app.config["PORT"], debug=app.config["DEBUG"])
