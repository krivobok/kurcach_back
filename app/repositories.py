from __future__ import annotations

import json
import secrets
import sqlite3
from datetime import datetime, timezone
from typing import Any

from .database import get_db
from .models import Achievement, ChatMessage, Game, Move, PlayerStats, Room, User


def utcnow() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def make_slug(prefix: str = "room") -> str:
    return f"{prefix}-{secrets.token_hex(4)}"


class RepositoryError(RuntimeError):
    pass


class NotFoundError(RepositoryError):
    pass


class ConflictError(RepositoryError):
    pass


class UserRepository:
    def create(
        self,
        username: str,
        password_hash: str,
        display_name: str | None = None,
        email: str | None = None,
        avatar_url: str | None = None,
        is_admin: bool = False,
        rating: int = 1000,
    ) -> User:
        db = get_db()
        try:
            cur = db.execute(
                """
                INSERT INTO users(username, password_hash, display_name, email, avatar_url, is_admin, rating)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (username, password_hash, display_name or username, email, avatar_url, int(is_admin), rating),
            )
            user_id = int(cur.lastrowid)
            db.execute(
                """
                INSERT INTO user_stats(user_id, rating)
                VALUES (?, ?)
                """,
                (user_id, rating),
            )
            db.commit()
        except sqlite3.IntegrityError as exc:
            raise ConflictError("Username or email is already used") from exc
        return self.get_by_id(user_id)

    def get_by_id(self, user_id: int) -> User:
        row = get_db().execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        if row is None:
            raise NotFoundError("User not found")
        return User.from_row(row)

    def get_by_username(self, username: str) -> User | None:
        row = get_db().execute("SELECT * FROM users WHERE lower(username) = lower(?)", (username,)).fetchone()
        return User.from_row(row) if row else None

    def list(self, limit: int = 50, offset: int = 0) -> list[User]:
        rows = get_db().execute(
            "SELECT * FROM users ORDER BY created_at DESC, id DESC LIMIT ? OFFSET ?",
            (limit, offset),
        ).fetchall()
        return [User.from_row(row) for row in rows]

    def count(self) -> int:
        row = get_db().execute("SELECT COUNT(*) AS count FROM users").fetchone()
        return int(row["count"])

    def admin_rows(self, limit: int = 50, offset: int = 0, query: str | None = None) -> list[dict[str, Any]]:
        params: list[Any] = []
        where = ""
        if query:
            where = "WHERE users.username LIKE ? OR users.display_name LIKE ? OR users.email LIKE ?"
            like = f"%{query.strip()}%"
            params.extend([like, like, like])
        params.extend([limit, offset])
        rows = get_db().execute(
            f"""
            SELECT users.id,
                   users.username,
                   users.display_name,
                   users.email,
                   users.avatar_url,
                   users.status,
                   users.rating,
                   users.created_at,
                   users.last_seen_at,
                   users.is_admin,
                   COALESCE(user_stats.games_played, 0) AS games_played,
                   COALESCE(user_stats.wins, 0) AS wins,
                   COALESCE(user_stats.losses, 0) AS losses,
                   COALESCE(user_stats.draws, 0) AS draws,
                   COALESCE(user_stats.moves_made, 0) AS moves_made
            FROM users
            LEFT JOIN user_stats ON user_stats.user_id = users.id
            {where}
            ORDER BY users.is_admin DESC, users.created_at DESC, users.id DESC
            LIMIT ? OFFSET ?
            """,
            tuple(params),
        ).fetchall()
        return [dict(row) for row in rows]

    def search(self, query: str, limit: int = 20) -> list[User]:
        like = f"%{query.strip()}%"
        rows = get_db().execute(
            """
            SELECT * FROM users
            WHERE username LIKE ? OR display_name LIKE ? OR email LIKE ?
            ORDER BY rating DESC, username ASC
            LIMIT ?
            """,
            (like, like, like, limit),
        ).fetchall()
        return [User.from_row(row) for row in rows]

    def update_profile(
        self,
        user_id: int,
        display_name: str | None = None,
        email: str | None = None,
        avatar_url: str | None = None,
    ) -> User:
        current = self.get_by_id(user_id)
        get_db().execute(
            """
            UPDATE users
            SET display_name = ?, email = ?, avatar_url = ?
            WHERE id = ?
            """,
            (
                display_name if display_name is not None else current.display_name,
                email if email is not None else current.email,
                avatar_url if avatar_url is not None else current.avatar_url,
                user_id,
            ),
        )
        get_db().commit()
        return self.get_by_id(user_id)

    def update_status(self, user_id: int, status: str) -> None:
        get_db().execute(
            "UPDATE users SET status = ?, last_seen_at = ? WHERE id = ?",
            (status, utcnow(), user_id),
        )
        get_db().commit()

    def set_admin(self, user_id: int, is_admin: bool) -> User:
        get_db().execute(
            "UPDATE users SET is_admin = ? WHERE id = ?",
            (int(is_admin), user_id),
        )
        get_db().commit()
        return self.get_by_id(user_id)

    def update_rating(self, user_id: int, rating: int) -> None:
        db = get_db()
        db.execute("UPDATE users SET rating = ? WHERE id = ?", (rating, user_id))
        db.execute("UPDATE user_stats SET rating = ?, updated_at = ? WHERE user_id = ?", (rating, utcnow(), user_id))
        db.commit()

    def create_token(self, user_id: int, token_hash: str, expires_at: str) -> None:
        get_db().execute(
            "INSERT INTO auth_tokens(user_id, token_hash, expires_at) VALUES (?, ?, ?)",
            (user_id, token_hash, expires_at),
        )
        get_db().commit()

    def find_token_user(self, token_hash: str, now: str) -> User | None:
        row = get_db().execute(
            """
            SELECT users.*
            FROM auth_tokens
            JOIN users ON users.id = auth_tokens.user_id
            WHERE token_hash = ? AND revoked_at IS NULL AND expires_at > ?
            """,
            (token_hash, now),
        ).fetchone()
        return User.from_row(row) if row else None

    def revoke_token(self, token_hash: str) -> bool:
        cur = get_db().execute(
            "UPDATE auth_tokens SET revoked_at = ? WHERE token_hash = ? AND revoked_at IS NULL",
            (utcnow(), token_hash),
        )
        get_db().commit()
        return cur.rowcount > 0

    def revoke_user_tokens(self, user_id: int) -> int:
        cur = get_db().execute(
            "UPDATE auth_tokens SET revoked_at = ? WHERE user_id = ? AND revoked_at IS NULL",
            (utcnow(), user_id),
        )
        get_db().commit()
        return int(cur.rowcount)

    def delete(self, user_id: int) -> bool:
        cur = get_db().execute("DELETE FROM users WHERE id = ?", (user_id,))
        get_db().commit()
        return cur.rowcount > 0


class RoomRepository:
    def create(
        self,
        name: str,
        created_by: int | None,
        mode: str = "public",
        board_size: int = 3,
        win_length: int = 3,
        max_players: int = 2,
    ) -> Room:
        slug = make_slug("room")
        db = get_db()
        cur = db.execute(
            """
            INSERT INTO rooms(slug, name, mode, board_size, win_length, max_players, created_by, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (slug, name, mode, board_size, win_length, max_players, created_by, utcnow()),
        )
        db.commit()
        return self.get(int(cur.lastrowid))

    def get(self, room_id: int) -> Room:
        row = get_db().execute("SELECT * FROM rooms WHERE id = ?", (room_id,)).fetchone()
        if row is None:
            raise NotFoundError("Room not found")
        return Room.from_row(row)

    def get_by_slug(self, slug: str) -> Room | None:
        row = get_db().execute("SELECT * FROM rooms WHERE slug = ?", (slug,)).fetchone()
        return Room.from_row(row) if row else None

    def list(self, status: str | None = None, limit: int = 50, offset: int = 0) -> list[Room]:
        if status:
            rows = get_db().execute(
                """
                SELECT * FROM rooms
                WHERE status = ?
                ORDER BY updated_at DESC, id DESC
                LIMIT ? OFFSET ?
                """,
                (status, limit, offset),
            ).fetchall()
        else:
            rows = get_db().execute(
                "SELECT * FROM rooms ORDER BY updated_at DESC, id DESC LIMIT ? OFFSET ?",
                (limit, offset),
            ).fetchall()
        return [Room.from_row(row) for row in rows]

    def count(self, status: str | None = None) -> int:
        if status:
            row = get_db().execute("SELECT COUNT(*) AS count FROM rooms WHERE status = ?", (status,)).fetchone()
        else:
            row = get_db().execute("SELECT COUNT(*) AS count FROM rooms").fetchone()
        return int(row["count"])

    def delete(self, room_id: int) -> bool:
        cur = get_db().execute("DELETE FROM rooms WHERE id = ?", (room_id,))
        get_db().commit()
        return cur.rowcount > 0

    def update_status(self, room_id: int, status: str) -> Room:
        get_db().execute(
            "UPDATE rooms SET status = ?, updated_at = ? WHERE id = ?",
            (status, utcnow(), room_id),
        )
        get_db().commit()
        return self.get(room_id)

    def set_current_game(self, room_id: int, game_id: int | None, status: str | None = None) -> Room:
        room = self.get(room_id)
        get_db().execute(
            """
            UPDATE rooms
            SET current_game_id = ?, status = ?, updated_at = ?
            WHERE id = ?
            """,
            (game_id, status or room.status, utcnow(), room_id),
        )
        get_db().commit()
        return self.get(room_id)

    def add_player(self, room_id: int, user_id: int, symbol: str | None = None, ready: bool = False) -> dict[str, Any]:
        players = self.players(room_id)
        active_symbols = {player["symbol"] for player in players if player["left_at"] is None}
        chosen = symbol or ("X" if "X" not in active_symbols else "O")
        seat = 1 if chosen == "X" else 2
        try:
            get_db().execute(
                """
                INSERT INTO room_players(room_id, user_id, symbol, seat, is_ready)
                VALUES (?, ?, ?, ?, ?)
                """,
                (room_id, user_id, chosen, seat, int(ready)),
            )
            get_db().commit()
        except sqlite3.IntegrityError as exc:
            raise ConflictError("User cannot join this room with requested symbol") from exc
        return self.player(room_id, user_id)

    def player(self, room_id: int, user_id: int) -> dict[str, Any]:
        row = get_db().execute(
            """
            SELECT rp.*, users.username, users.display_name, users.rating
            FROM room_players rp
            JOIN users ON users.id = rp.user_id
            WHERE rp.room_id = ? AND rp.user_id = ?
            """,
            (room_id, user_id),
        ).fetchone()
        if row is None:
            raise NotFoundError("Player is not in room")
        return dict(row)

    def players(self, room_id: int, active_only: bool = True) -> list[dict[str, Any]]:
        if active_only:
            rows = get_db().execute(
                """
                SELECT rp.*, users.username, users.display_name, users.rating
                FROM room_players rp
                JOIN users ON users.id = rp.user_id
                WHERE rp.room_id = ? AND rp.left_at IS NULL
                ORDER BY rp.seat ASC
                """,
                (room_id,),
            ).fetchall()
        else:
            rows = get_db().execute(
                """
                SELECT rp.*, users.username, users.display_name, users.rating
                FROM room_players rp
                JOIN users ON users.id = rp.user_id
                WHERE rp.room_id = ?
                ORDER BY rp.seat ASC
                """,
                (room_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def leave(self, room_id: int, user_id: int) -> None:
        get_db().execute(
            "UPDATE room_players SET left_at = ? WHERE room_id = ? AND user_id = ? AND left_at IS NULL",
            (utcnow(), room_id, user_id),
        )
        get_db().commit()

    def set_ready(self, room_id: int, user_id: int, ready: bool) -> dict[str, Any]:
        get_db().execute(
            "UPDATE room_players SET is_ready = ? WHERE room_id = ? AND user_id = ?",
            (int(ready), room_id, user_id),
        )
        get_db().commit()
        return self.player(room_id, user_id)

    def active_count(self, room_id: int) -> int:
        row = get_db().execute(
            "SELECT COUNT(*) AS count FROM room_players WHERE room_id = ? AND left_at IS NULL",
            (room_id,),
        ).fetchone()
        return int(row["count"])

    def find_waiting_room(self, board_size: int, win_length: int, exclude_user_id: int) -> Room | None:
        row = get_db().execute(
            """
            SELECT rooms.*
            FROM rooms
            WHERE rooms.status = 'waiting'
              AND rooms.mode = 'matchmaking'
              AND rooms.board_size = ?
              AND rooms.win_length = ?
              AND rooms.id NOT IN (
                  SELECT room_id FROM room_players
                  WHERE user_id = ? AND left_at IS NULL
              )
            ORDER BY rooms.created_at ASC
            LIMIT 1
            """,
            (board_size, win_length, exclude_user_id),
        ).fetchone()
        return Room.from_row(row) if row else None


class GameRepository:
    def create(self, room_id: int, board_size: int, win_length: int, player_x_id: int | None, player_o_id: int | None) -> Game:
        cur = get_db().execute(
            """
            INSERT INTO games(room_id, board_size, win_length, player_x_id, player_o_id, status, started_at)
            VALUES (?, ?, ?, ?, ?, 'playing', ?)
            """,
            (room_id, board_size, win_length, player_x_id, player_o_id, utcnow()),
        )
        get_db().commit()
        return self.get(int(cur.lastrowid))

    def get(self, game_id: int) -> Game:
        row = get_db().execute("SELECT * FROM games WHERE id = ?", (game_id,)).fetchone()
        if row is None:
            raise NotFoundError("Game not found")
        return Game.from_row(row)

    def list_for_room(self, room_id: int) -> list[Game]:
        rows = get_db().execute(
            "SELECT * FROM games WHERE room_id = ? ORDER BY created_at DESC, id DESC",
            (room_id,),
        ).fetchall()
        return [Game.from_row(row) for row in rows]

    def recent_for_user(self, user_id: int, limit: int = 10) -> list[dict[str, Any]]:
        rows = get_db().execute(
            """
            SELECT games.*,
                   rooms.name AS room_name,
                   rooms.mode AS room_mode,
                   rooms.status AS room_status,
                   x.username AS player_x_username,
                   o.username AS player_o_username
            FROM games
            JOIN rooms ON rooms.id = games.room_id
            LEFT JOIN users AS x ON x.id = games.player_x_id
            LEFT JOIN users AS o ON o.id = games.player_o_id
            WHERE games.player_x_id = ? OR games.player_o_id = ?
            ORDER BY games.created_at DESC, games.id DESC
            LIMIT ?
            """,
            (user_id, user_id, limit),
        ).fetchall()
        return [dict(row) for row in rows]

    def count(self, status: str | None = None) -> int:
        if status:
            row = get_db().execute("SELECT COUNT(*) AS count FROM games WHERE status = ?", (status,)).fetchone()
        else:
            row = get_db().execute("SELECT COUNT(*) AS count FROM games").fetchone()
        return int(row["count"])

    def update_turn_and_count(self, game_id: int, next_turn: str, move_count: int) -> Game:
        get_db().execute(
            """
            UPDATE games
            SET current_turn = ?, move_count = ?
            WHERE id = ?
            """,
            (next_turn, move_count, game_id),
        )
        get_db().commit()
        return self.get(game_id)

    def finish(
        self,
        game_id: int,
        winner_symbol: str | None,
        winner_user_id: int | None,
        draw: bool,
        winning_line: list[tuple[int, int]] | None,
        move_count: int,
    ) -> Game:
        get_db().execute(
            """
            UPDATE games
            SET status = 'finished',
                winner_symbol = ?,
                winner_user_id = ?,
                draw = ?,
                winning_line = ?,
                move_count = ?,
                finished_at = ?
            WHERE id = ?
            """,
            (
                winner_symbol,
                winner_user_id,
                int(draw),
                json.dumps(winning_line or []),
                move_count,
                utcnow(),
                game_id,
            ),
        )
        get_db().commit()
        return self.get(game_id)

    def add_move(self, game_id: int, user_id: int | None, symbol: str, row: int, col: int, move_number: int, board_after: str) -> Move:
        try:
            cur = get_db().execute(
                """
                INSERT INTO moves(game_id, user_id, symbol, row, col, move_number, board_after)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (game_id, user_id, symbol, row, col, move_number, board_after),
            )
            get_db().commit()
        except sqlite3.IntegrityError as exc:
            raise ConflictError("Move conflicts with existing game state") from exc
        return self.move(int(cur.lastrowid))

    def move(self, move_id: int) -> Move:
        row = get_db().execute("SELECT * FROM moves WHERE id = ?", (move_id,)).fetchone()
        if row is None:
            raise NotFoundError("Move not found")
        return Move.from_row(row)

    def moves(self, game_id: int) -> list[Move]:
        rows = get_db().execute(
            "SELECT * FROM moves WHERE game_id = ? ORDER BY move_number ASC",
            (game_id,),
        ).fetchall()
        return [Move.from_row(row) for row in rows]

    def latest_move(self, game_id: int) -> Move | None:
        row = get_db().execute(
            "SELECT * FROM moves WHERE game_id = ? ORDER BY move_number DESC LIMIT 1",
            (game_id,),
        ).fetchone()
        return Move.from_row(row) if row else None

    def add_event(self, game_id: int, event_type: str, payload: dict[str, Any]) -> None:
        get_db().execute(
            "INSERT INTO game_events(game_id, event_type, payload) VALUES (?, ?, ?)",
            (game_id, event_type, json.dumps(payload, ensure_ascii=True)),
        )
        get_db().commit()

    def events(self, game_id: int) -> list[dict[str, Any]]:
        rows = get_db().execute(
            "SELECT * FROM game_events WHERE game_id = ? ORDER BY id ASC",
            (game_id,),
        ).fetchall()
        result = []
        for row in rows:
            item = dict(row)
            item["payload"] = json.loads(item["payload"] or "{}")
            result.append(item)
        return result


class ChatRepository:
    def add(self, room_id: int, user_id: int | None, body: str, kind: str = "user") -> ChatMessage:
        cur = get_db().execute(
            "INSERT INTO chat_messages(room_id, user_id, body, kind) VALUES (?, ?, ?, ?)",
            (room_id, user_id, body, kind),
        )
        get_db().commit()
        return self.get(int(cur.lastrowid))

    def get(self, message_id: int) -> ChatMessage:
        row = get_db().execute("SELECT * FROM chat_messages WHERE id = ?", (message_id,)).fetchone()
        if row is None:
            raise NotFoundError("Message not found")
        return ChatMessage.from_row(row)

    def list_for_room(self, room_id: int, limit: int = 50) -> list[ChatMessage]:
        rows = get_db().execute(
            """
            SELECT * FROM (
                SELECT * FROM chat_messages
                WHERE room_id = ?
                ORDER BY id DESC
                LIMIT ?
            )
            ORDER BY id ASC
            """,
            (room_id, limit),
        ).fetchall()
        return [ChatMessage.from_row(row) for row in rows]


class StatsRepository:
    def get(self, user_id: int) -> PlayerStats:
        self.ensure(user_id)
        row = get_db().execute("SELECT * FROM user_stats WHERE user_id = ?", (user_id,)).fetchone()
        if row is None:
            raise NotFoundError("Stats not found")
        return PlayerStats.from_row(row)

    def ensure(self, user_id: int, rating: int = 1000) -> None:
        get_db().execute(
            "INSERT OR IGNORE INTO user_stats(user_id, rating) VALUES (?, ?)",
            (user_id, rating),
        )
        get_db().commit()

    def add_move(self, user_id: int | None) -> None:
        if user_id is None:
            return
        self.ensure(user_id)
        get_db().execute(
            "UPDATE user_stats SET moves_made = moves_made + 1, updated_at = ? WHERE user_id = ?",
            (utcnow(), user_id),
        )
        get_db().commit()

    def apply_result(self, player_x_id: int | None, player_o_id: int | None, winner_user_id: int | None, draw: bool) -> None:
        for user_id in (player_x_id, player_o_id):
            if user_id is not None:
                self.ensure(user_id)
        if draw:
            for user_id in (player_x_id, player_o_id):
                if user_id is not None:
                    self._draw(user_id)
            return
        loser_id = None
        if winner_user_id == player_x_id:
            loser_id = player_o_id
        elif winner_user_id == player_o_id:
            loser_id = player_x_id
        if winner_user_id is not None:
            self._win(winner_user_id)
        if loser_id is not None:
            self._loss(loser_id)

    def _win(self, user_id: int) -> None:
        db = get_db()
        db.execute(
            """
            UPDATE user_stats
            SET games_played = games_played + 1,
                wins = wins + 1,
                current_streak = current_streak + 1,
                best_streak = CASE WHEN current_streak + 1 > best_streak THEN current_streak + 1 ELSE best_streak END,
                rating = rating + 24,
                updated_at = ?
            WHERE user_id = ?
            """,
            (utcnow(), user_id),
        )
        db.execute("UPDATE users SET rating = rating + 24 WHERE id = ?", (user_id,))
        db.commit()

    def _loss(self, user_id: int) -> None:
        db = get_db()
        db.execute(
            """
            UPDATE user_stats
            SET games_played = games_played + 1,
                losses = losses + 1,
                current_streak = 0,
                rating = CASE WHEN rating - 16 < 100 THEN 100 ELSE rating - 16 END,
                updated_at = ?
            WHERE user_id = ?
            """,
            (utcnow(), user_id),
        )
        db.execute("UPDATE users SET rating = CASE WHEN rating - 16 < 100 THEN 100 ELSE rating - 16 END WHERE id = ?", (user_id,))
        db.commit()

    def _draw(self, user_id: int) -> None:
        db = get_db()
        db.execute(
            """
            UPDATE user_stats
            SET games_played = games_played + 1,
                draws = draws + 1,
                current_streak = 0,
                rating = rating + 4,
                updated_at = ?
            WHERE user_id = ?
            """,
            (utcnow(), user_id),
        )
        db.execute("UPDATE users SET rating = rating + 4 WHERE id = ?", (user_id,))
        db.commit()

    def leaderboard(self, limit: int = 20) -> list[dict[str, Any]]:
        rows = get_db().execute(
            """
            SELECT user_stats.*, users.username, users.display_name, users.avatar_url
            FROM user_stats
            JOIN users ON users.id = user_stats.user_id
            ORDER BY user_stats.rating DESC, user_stats.wins DESC, users.username ASC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [dict(row) for row in rows]

    def achievement_catalog(self) -> list[dict[str, Any]]:
        rows = get_db().execute(
            """
            SELECT achievements.*,
                   COUNT(user_achievements.id) AS unlocked_count
            FROM achievements
            LEFT JOIN user_achievements ON user_achievements.achievement_id = achievements.id
            GROUP BY achievements.id
            ORDER BY achievements.points DESC, achievements.id ASC
            """
        ).fetchall()
        return [dict(row) for row in rows]

    def unlock_achievement(self, user_id: int, code: str) -> bool:
        row = get_db().execute("SELECT id FROM achievements WHERE code = ?", (code,)).fetchone()
        if row is None:
            return False
        try:
            get_db().execute(
                "INSERT INTO user_achievements(user_id, achievement_id) VALUES (?, ?)",
                (user_id, row["id"]),
            )
            get_db().commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def achievements(self, user_id: int) -> list[Achievement]:
        rows = get_db().execute(
            """
            SELECT achievements.*
            FROM user_achievements
            JOIN achievements ON achievements.id = user_achievements.achievement_id
            WHERE user_achievements.user_id = ?
            ORDER BY user_achievements.unlocked_at ASC
            """,
            (user_id,),
        ).fetchall()
        return [Achievement.from_row(row) for row in rows]

    def award_automatic(self, user_id: int, game: Game) -> list[str]:
        stats = self.get(user_id)
        unlocked: list[str] = []
        checks = [
            (stats.wins >= 1, "first_win"),
            (stats.games_played >= 5, "five_games"),
            (stats.current_streak >= 3, "win_streak_3"),
            (game.move_count <= 5 and game.winner_user_id == user_id, "fast_finish"),
            (game.board_size > 3, "large_board"),
        ]
        for condition, code in checks:
            if condition and self.unlock_achievement(user_id, code):
                unlocked.append(code)
        return unlocked


class MatchmakingRepository:
    def queue(self, user_id: int, board_size: int, win_length: int) -> dict[str, Any]:
        try:
            get_db().execute(
                """
                INSERT INTO matchmaking_queue(user_id, board_size, win_length)
                VALUES (?, ?, ?)
                """,
                (user_id, board_size, win_length),
            )
            get_db().commit()
        except sqlite3.IntegrityError:
            get_db().execute(
                """
                UPDATE matchmaking_queue
                SET board_size = ?, win_length = ?, created_at = ?, matched_room_id = NULL
                WHERE user_id = ? AND status = 'queued'
                """,
                (board_size, win_length, utcnow(), user_id),
            )
            get_db().commit()
        return self.get_active(user_id)

    def get_active(self, user_id: int) -> dict[str, Any]:
        row = get_db().execute(
            """
            SELECT * FROM matchmaking_queue
            WHERE user_id = ? AND status = 'queued'
            """,
            (user_id,),
        ).fetchone()
        if row is None:
            raise NotFoundError("Queue item not found")
        return dict(row)

    def cancel(self, user_id: int) -> bool:
        cur = get_db().execute(
            "UPDATE matchmaking_queue SET status = 'cancelled' WHERE user_id = ? AND status = 'queued'",
            (user_id,),
        )
        get_db().commit()
        return cur.rowcount > 0

    def find_candidate(self, user_id: int, board_size: int, win_length: int) -> dict[str, Any] | None:
        row = get_db().execute(
            """
            SELECT mq.*, users.rating
            FROM matchmaking_queue mq
            JOIN users ON users.id = mq.user_id
            WHERE mq.status = 'queued'
              AND mq.user_id != ?
              AND mq.board_size = ?
              AND mq.win_length = ?
            ORDER BY mq.created_at ASC
            LIMIT 1
            """,
            (user_id, board_size, win_length),
        ).fetchone()
        return dict(row) if row else None

    def mark_matched(self, user_ids: list[int], room_id: int) -> None:
        if not user_ids:
            return
        placeholders = ",".join("?" for _ in user_ids)
        get_db().execute(
            f"""
            UPDATE matchmaking_queue
            SET status = 'matched', matched_room_id = ?
            WHERE status = 'queued' AND user_id IN ({placeholders})
            """,
            (room_id, *user_ids),
        )
        get_db().commit()


class AuditRepository:
    def add(self, actor_id: int | None, action: str, entity_type: str, entity_id: int | None, payload: dict[str, Any] | None = None) -> None:
        get_db().execute(
            """
            INSERT INTO audit_log(actor_id, action, entity_type, entity_id, payload)
            VALUES (?, ?, ?, ?, ?)
            """,
            (actor_id, action, entity_type, entity_id, json.dumps(payload or {}, ensure_ascii=True)),
        )
        get_db().commit()

    def list(self, limit: int = 100) -> list[dict[str, Any]]:
        rows = get_db().execute(
            "SELECT * FROM audit_log ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
        result = []
        for row in rows:
            item = dict(row)
            item["payload"] = json.loads(item["payload"] or "{}")
            result.append(item)
        return result
