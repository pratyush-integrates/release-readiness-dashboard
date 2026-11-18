"""Release Readiness Dashboard: Flask app factory."""
from flask import Flask

from .config import Config


def create_app(config: Config | None = None) -> Flask:
    app = Flask(__name__)
    app.config["RRD"] = config or Config.from_env()
    app.secret_key = app.config["RRD"].secret_key

    from .routes import bp

    app.register_blueprint(bp)
    return app
