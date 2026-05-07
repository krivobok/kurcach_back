import os

from app import create_app
from app.extensions import socketio, socketio_available


app = create_app()


if __name__ == "__main__":
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "5000"))
    debug = os.environ.get("FLASK_DEBUG", "1") == "1"
    use_reloader = os.environ.get("USE_RELOADER", "0") == "1"
    if socketio_available:
        socketio.run(app, host=host, port=port, debug=debug, use_reloader=use_reloader, allow_unsafe_werkzeug=True)
    else:
        app.run(host=host, port=port, debug=debug, use_reloader=use_reloader)
