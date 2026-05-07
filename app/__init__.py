from __future__ import annotations

from pathlib import Path

from flask import Flask

from config import Config

from .database import close_db, init_db
from .extensions import socketio


def create_app(config_object: type[Config] | None = None) -> Flask:
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config_object or Config)
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    Path(app.config["DATABASE_PATH"]).parent.mkdir(parents=True, exist_ok=True)

    init_db(app)
    app.teardown_appcontext(close_db)

    from .controllers.api import api_bp
    from .controllers.docs import docs_bp
    from .controllers.pages import pages_bp
    from .controllers.sockets import register_socket_handlers

    app.register_blueprint(api_bp, url_prefix="/api")
    app.register_blueprint(docs_bp)
    app.register_blueprint(pages_bp)
    register_socket_handlers(socketio)
    socketio.init_app(app, cors_allowed_origins="*", async_mode=app.config.get("SOCKETIO_ASYNC_MODE", "threading"))

    return app
