from __future__ import annotations

from typing import Any, Callable


socketio_available = True

try:
    from flask_socketio import SocketIO, emit, join_room, leave_room
except Exception:  # pragma: no cover - exercised only when optional dependency is missing
    socketio_available = False

    class SocketIO:  # type: ignore[no-redef]
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            self.handlers: dict[str, Callable[..., Any]] = {}

        def init_app(self, app: Any, **kwargs: Any) -> None:
            return None

        def on(self, event: str, namespace: str | None = None) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
            def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
                key = f"{namespace or '/'}:{event}"
                self.handlers[key] = func
                return func

            return decorator

        def emit(self, *args: Any, **kwargs: Any) -> None:
            return None

        def run(self, app: Any, **kwargs: Any) -> None:
            app.run(**kwargs)

    def emit(*args: Any, **kwargs: Any) -> None:  # type: ignore[no-redef]
        return None

    def join_room(room: str) -> None:  # type: ignore[no-redef]
        return None

    def leave_room(room: str) -> None:  # type: ignore[no-redef]
        return None


socketio = SocketIO(cors_allowed_origins="*", async_mode="threading")
