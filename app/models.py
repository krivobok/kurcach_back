from __future__ import annotations

from dataclasses import dataclass
from typing import Any


def _dict(row: Any | None) -> dict[str, Any] | None:
    if row is None:
        return None
    return dict(row)


@dataclass(frozen=True)
class User:
    id: int
    username: str
    password_hash: str
    display_name: str
    email: str | None
    avatar_url: str | None
    status: str
    rating: int
    created_at: str
    last_seen_at: str | None
    is_admin: bool

    @classmethod
    def from_row(cls, row: Any) -> "User":
        data = _dict(row) or {}
        data["is_admin"] = bool(data.get("is_admin"))
        return cls(**data)

    def public(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "username": self.username,
            "display_name": self.display_name,
            "email": self.email,
            "avatar_url": self.avatar_url,
            "status": self.status,
            "rating": self.rating,
            "created_at": self.created_at,
            "last_seen_at": self.last_seen_at,
            "is_admin": self.is_admin,
        }


@dataclass(frozen=True)
class Room:
    id: int
    slug: str
    name: str
    mode: str
    status: str
    board_size: int
    win_length: int
    max_players: int
    created_by: int | None
    current_game_id: int | None
    created_at: str
    updated_at: str

    @classmethod
    def from_row(cls, row: Any) -> "Room":
        return cls(**(_dict(row) or {}))

    def public(self) -> dict[str, Any]:
        return self.__dict__.copy()


@dataclass(frozen=True)
class Game:
    id: int
    room_id: int
    status: str
    board_size: int
    win_length: int
    player_x_id: int | None
    player_o_id: int | None
    current_turn: str
    winner_symbol: str | None
    winner_user_id: int | None
    draw: bool
    winning_line: str | None
    move_count: int
    started_at: str | None
    finished_at: str | None
    created_at: str

    @classmethod
    def from_row(cls, row: Any) -> "Game":
        data = _dict(row) or {}
        data["draw"] = bool(data.get("draw"))
        return cls(**data)

    def public(self) -> dict[str, Any]:
        return self.__dict__.copy()


@dataclass(frozen=True)
class Move:
    id: int
    game_id: int
    user_id: int | None
    symbol: str
    row: int
    col: int
    move_number: int
    board_after: str
    created_at: str

    @classmethod
    def from_row(cls, row: Any) -> "Move":
        return cls(**(_dict(row) or {}))

    def public(self) -> dict[str, Any]:
        return self.__dict__.copy()


@dataclass(frozen=True)
class ChatMessage:
    id: int
    room_id: int
    user_id: int | None
    body: str
    kind: str
    created_at: str

    @classmethod
    def from_row(cls, row: Any) -> "ChatMessage":
        return cls(**(_dict(row) or {}))

    def public(self) -> dict[str, Any]:
        return self.__dict__.copy()


@dataclass(frozen=True)
class PlayerStats:
    user_id: int
    games_played: int
    wins: int
    losses: int
    draws: int
    moves_made: int
    current_streak: int
    best_streak: int
    rating: int
    updated_at: str

    @classmethod
    def from_row(cls, row: Any) -> "PlayerStats":
        return cls(**(_dict(row) or {}))

    def public(self) -> dict[str, Any]:
        total = max(self.games_played, 1)
        return {
            **self.__dict__,
            "win_rate": round(self.wins / total, 4),
            "loss_rate": round(self.losses / total, 4),
            "draw_rate": round(self.draws / total, 4),
        }


@dataclass(frozen=True)
class Achievement:
    id: int
    code: str
    title: str
    description: str
    points: int

    @classmethod
    def from_row(cls, row: Any) -> "Achievement":
        return cls(**(_dict(row) or {}))
