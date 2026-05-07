from __future__ import annotations

from typing import Any

from ..models import User
from ..repositories import AuditRepository, GameRepository, NotFoundError, RoomRepository, StatsRepository, UserRepository


class AdminServiceError(RuntimeError):
    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.status_code = status_code


class AdminService:
    USER_STATUSES = {"online", "offline", "banned"}
    ROOM_STATUSES = {"waiting", "playing", "finished", "closed"}

    def __init__(self) -> None:
        self.users = UserRepository()
        self.rooms = RoomRepository()
        self.games = GameRepository()
        self.stats = StatsRepository()
        self.audit = AuditRepository()

    def dashboard(self) -> dict[str, Any]:
        return {
            "users_total": self.users.count(),
            "rooms_total": self.rooms.count(),
            "rooms_waiting": self.rooms.count("waiting"),
            "rooms_playing": self.rooms.count("playing"),
            "rooms_finished": self.rooms.count("finished"),
            "rooms_closed": self.rooms.count("closed"),
            "games_total": self.games.count(),
            "games_playing": self.games.count("playing"),
            "games_finished": self.games.count("finished"),
            "latest_audit": self.audit.list(10),
        }

    def list_users(self, limit: int = 50, offset: int = 0, query: str | None = None) -> list[dict[str, Any]]:
        rows = self.users.admin_rows(limit, offset, query)
        for row in rows:
            row["is_admin"] = bool(row["is_admin"])
            row["role"] = "admin" if row["is_admin"] else "client"
        return rows

    def user_detail(self, user_id: int) -> dict[str, Any]:
        user = self._user_or_404(user_id)
        return {
            "user": {**user.public(), "role": "admin" if user.is_admin else "client"},
            "stats": self.stats.get(user.id).public(),
            "achievements": [achievement.__dict__ for achievement in self.stats.achievements(user.id)],
        }

    def set_role(self, actor: User, user_id: int, is_admin: bool) -> dict[str, Any]:
        target = self._user_or_404(user_id)
        if target.id == actor.id and not is_admin:
            raise AdminServiceError("Admin cannot remove own admin role")
        updated = self.users.set_admin(target.id, is_admin)
        self.audit.add(actor.id, "admin_set_role", "user", target.id, {"is_admin": is_admin})
        return {**updated.public(), "role": "admin" if updated.is_admin else "client"}

    def set_status(self, actor: User, user_id: int, status: str) -> dict[str, Any]:
        status = status.strip().lower()
        if status not in self.USER_STATUSES:
            raise AdminServiceError("Unsupported user status")
        target = self._user_or_404(user_id)
        if target.id == actor.id and status == "banned":
            raise AdminServiceError("Admin cannot ban own account")
        self.users.update_status(target.id, status)
        revoked_tokens = 0
        if status == "banned":
            revoked_tokens = self.users.revoke_user_tokens(target.id)
        self.audit.add(actor.id, "admin_set_status", "user", target.id, {"status": status, "revoked_tokens": revoked_tokens})
        updated = self.users.get_by_id(target.id)
        return {**updated.public(), "role": "admin" if updated.is_admin else "client", "revoked_tokens": revoked_tokens}

    def revoke_tokens(self, actor: User, user_id: int) -> dict[str, Any]:
        target = self._user_or_404(user_id)
        revoked = self.users.revoke_user_tokens(target.id)
        self.audit.add(actor.id, "admin_revoke_tokens", "user", target.id, {"revoked_tokens": revoked})
        return {"user": target.public(), "revoked_tokens": revoked}

    def delete_user(self, actor: User, user_id: int) -> dict[str, Any]:
        target = self._user_or_404(user_id)
        if target.id == actor.id:
            raise AdminServiceError("Admin cannot delete own account")
        deleted = self.users.delete(target.id)
        self.audit.add(actor.id, "admin_delete_user", "user", target.id, {"username": target.username, "deleted": deleted})
        return {"deleted": deleted, "user_id": target.id}

    def list_rooms(self, limit: int = 50, offset: int = 0, status: str | None = None) -> list[dict[str, Any]]:
        rooms = self.rooms.list(status, limit, offset)
        result = []
        for room in rooms:
            data = room.public()
            data["players"] = self.rooms.players(room.id)
            result.append(data)
        return result

    def set_room_status(self, actor: User, room_id: int, status: str) -> dict[str, Any]:
        status = status.strip().lower()
        if status not in self.ROOM_STATUSES:
            raise AdminServiceError("Unsupported room status")
        try:
            room = self.rooms.get(room_id)
        except NotFoundError as exc:
            raise AdminServiceError("Room not found", 404) from exc
        if status in {"finished", "closed"} and room.current_game_id:
            game = self.games.get(room.current_game_id)
            if game.status == "playing":
                self.games.finish(game.id, None, None, True, [], game.move_count)
                self.games.add_event(game.id, "admin_finished_game", {"actor_id": actor.id, "room_status": status})
        room = self.rooms.update_status(room_id, status)
        self.audit.add(actor.id, "admin_set_room_status", "room", room.id, {"status": status})
        data = room.public()
        data["players"] = self.rooms.players(room.id)
        return data

    def delete_room(self, actor: User, room_id: int) -> dict[str, Any]:
        try:
            room = self.rooms.get(room_id)
        except NotFoundError as exc:
            raise AdminServiceError("Room not found", 404) from exc
        if room.current_game_id:
            game = self.games.get(room.current_game_id)
            if game.status == "playing":
                self.games.finish(game.id, None, None, True, [], game.move_count)
                self.games.add_event(game.id, "admin_deleted_room", {"actor_id": actor.id})
        deleted = self.rooms.delete(room.id)
        self.audit.add(actor.id, "admin_delete_room", "room", room.id, {"name": room.name, "deleted": deleted})
        return {"deleted": deleted, "room_id": room.id}

    def _user_or_404(self, user_id: int) -> User:
        try:
            return self.users.get_by_id(user_id)
        except NotFoundError as exc:
            raise AdminServiceError("User not found", 404) from exc
