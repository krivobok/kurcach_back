from __future__ import annotations

from typing import Any

from flask import request

from ..extensions import emit, join_room, leave_room
from ..services.auth_service import AuthService
from ..services.game_service import GameService, GameServiceError


def _socket_user(payload: dict[str, Any] | None):
    payload = payload or {}
    token = payload.get("token")
    if not token:
        auth = request.headers.get("Authorization", "")
        if auth.lower().startswith("bearer "):
            token = auth.split(" ", 1)[1].strip()
    return AuthService().authenticate_token(token)


def _emit_error(message: str, code: str = "socket_error") -> None:
    emit("error", {"ok": False, "error": {"code": code, "message": message}})


def register_socket_handlers(socketio) -> None:
    @socketio.on("connect")
    def on_connect():
        emit("connected", {"ok": True, "sid": request.sid})

    @socketio.on("user.join")
    def on_user_join(payload):
        user = _socket_user(payload)
        if user is None:
            return _emit_error("Authentication required", "auth_required")
        join_room(f"user:{user.id}")
        emit("user.joined", {"ok": True, "user": user.public()})

    @socketio.on("room.subscribe")
    def on_room_subscribe(payload):
        room_id = int((payload or {}).get("room_id", 0))
        if room_id <= 0:
            return _emit_error("room_id is required")
        join_room(f"room:{room_id}")
        emit("room.snapshot", GameService().room_state(room_id))

    @socketio.on("room.unsubscribe")
    def on_room_unsubscribe(payload):
        room_id = int((payload or {}).get("room_id", 0))
        if room_id > 0:
            leave_room(f"room:{room_id}")
        emit("room.unsubscribed", {"ok": True, "room_id": room_id})

    @socketio.on("room.join")
    def on_room_join(payload):
        user = _socket_user(payload)
        if user is None:
            return _emit_error("Authentication required", "auth_required")
        try:
            room_id = int(payload.get("room_id"))
            data = GameService().join_room(user, room_id, payload.get("symbol"), bool(payload.get("ready", True)))
            join_room(f"room:{room_id}")
            emit("room.joined", data)
        except (TypeError, ValueError, GameServiceError) as exc:
            _emit_error(str(exc))

    @socketio.on("room.ready")
    def on_ready(payload):
        user = _socket_user(payload)
        if user is None:
            return _emit_error("Authentication required", "auth_required")
        try:
            room_id = int(payload.get("room_id"))
            emit("room.ready_changed", GameService().set_ready(user, room_id, bool(payload.get("ready", True))))
        except (TypeError, ValueError, GameServiceError) as exc:
            _emit_error(str(exc))

    @socketio.on("game.move")
    def on_game_move(payload):
        user = _socket_user(payload)
        if user is None:
            return _emit_error("Authentication required", "auth_required")
        try:
            data = GameService().make_move(
                actor=user,
                game_id=int(payload.get("game_id")),
                row=int(payload.get("row")),
                col=int(payload.get("col")),
            )
            emit("game.move_accepted", data)
        except (TypeError, ValueError, GameServiceError) as exc:
            _emit_error(str(exc))

    @socketio.on("chat.send")
    def on_chat(payload):
        user = _socket_user(payload)
        if user is None:
            return _emit_error("Authentication required", "auth_required")
        try:
            message = GameService().add_chat_message(user, int(payload.get("room_id")), str(payload.get("body", "")))
            emit("chat.sent", message)
        except (TypeError, ValueError, GameServiceError) as exc:
            _emit_error(str(exc))

    @socketio.on("matchmaking.queue")
    def on_matchmaking(payload):
        user = _socket_user(payload)
        if user is None:
            return _emit_error("Authentication required", "auth_required")
        try:
            result = GameService().queue_matchmaking(
                user,
                board_size=int((payload or {}).get("board_size", 3)),
                win_length=int((payload or {}).get("win_length", 3)),
            )
            emit("matchmaking.queued", result)
        except (TypeError, ValueError, GameServiceError) as exc:
            _emit_error(str(exc))
