from __future__ import annotations

from typing import Any

from ..extensions import socketio


class NotificationService:
    def room_updated(self, room_id: int, payload: dict[str, Any]) -> None:
        socketio.emit("room.updated", payload, room=f"room:{room_id}")

    def move_made(self, room_id: int, payload: dict[str, Any]) -> None:
        socketio.emit("game.move_made", payload, room=f"room:{room_id}")

    def game_finished(self, room_id: int, payload: dict[str, Any]) -> None:
        socketio.emit("game.finished", payload, room=f"room:{room_id}")

    def chat_message(self, room_id: int, payload: dict[str, Any]) -> None:
        socketio.emit("chat.message", payload, room=f"room:{room_id}")

    def matchmaking_matched(self, user_id: int, payload: dict[str, Any]) -> None:
        socketio.emit("matchmaking.matched", payload, room=f"user:{user_id}")
