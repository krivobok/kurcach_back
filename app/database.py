from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Iterable

from flask import Flask, current_app, g


SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    display_name TEXT NOT NULL,
    email TEXT UNIQUE,
    avatar_url TEXT,
    status TEXT NOT NULL DEFAULT 'offline',
    rating INTEGER NOT NULL DEFAULT 1000,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_seen_at TEXT,
    is_admin INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_users_rating ON users(rating DESC, username ASC);

CREATE TABLE IF NOT EXISTS auth_tokens (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at TEXT NOT NULL,
    revoked_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_auth_tokens_user ON auth_tokens(user_id, revoked_at);

CREATE TABLE IF NOT EXISTS rooms (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    slug TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    mode TEXT NOT NULL DEFAULT 'public',
    status TEXT NOT NULL DEFAULT 'waiting',
    board_size INTEGER NOT NULL DEFAULT 3,
    win_length INTEGER NOT NULL DEFAULT 3,
    max_players INTEGER NOT NULL DEFAULT 2,
    created_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    current_game_id INTEGER,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_rooms_status ON rooms(status, mode, updated_at DESC);

CREATE TABLE IF NOT EXISTS room_players (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    room_id INTEGER NOT NULL REFERENCES rooms(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    symbol TEXT NOT NULL CHECK(symbol IN ('X', 'O')),
    seat INTEGER NOT NULL,
    joined_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    left_at TEXT,
    is_ready INTEGER NOT NULL DEFAULT 0,
    UNIQUE(room_id, user_id),
    UNIQUE(room_id, symbol)
);

CREATE TABLE IF NOT EXISTS games (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    room_id INTEGER NOT NULL REFERENCES rooms(id) ON DELETE CASCADE,
    status TEXT NOT NULL DEFAULT 'waiting',
    board_size INTEGER NOT NULL DEFAULT 3,
    win_length INTEGER NOT NULL DEFAULT 3,
    player_x_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    player_o_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    current_turn TEXT NOT NULL DEFAULT 'X',
    winner_symbol TEXT,
    winner_user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    draw INTEGER NOT NULL DEFAULT 0,
    winning_line TEXT,
    move_count INTEGER NOT NULL DEFAULT 0,
    started_at TEXT,
    finished_at TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_games_room_status ON games(room_id, status, created_at DESC);

CREATE TABLE IF NOT EXISTS moves (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    game_id INTEGER NOT NULL REFERENCES games(id) ON DELETE CASCADE,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    symbol TEXT NOT NULL CHECK(symbol IN ('X', 'O')),
    row INTEGER NOT NULL,
    col INTEGER NOT NULL,
    move_number INTEGER NOT NULL,
    board_after TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(game_id, row, col),
    UNIQUE(game_id, move_number)
);

CREATE INDEX IF NOT EXISTS idx_moves_game_order ON moves(game_id, move_number ASC);

CREATE TABLE IF NOT EXISTS chat_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    room_id INTEGER NOT NULL REFERENCES rooms(id) ON DELETE CASCADE,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    body TEXT NOT NULL,
    kind TEXT NOT NULL DEFAULT 'user',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_chat_room_order ON chat_messages(room_id, id DESC);

CREATE TABLE IF NOT EXISTS matchmaking_queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    board_size INTEGER NOT NULL DEFAULT 3,
    win_length INTEGER NOT NULL DEFAULT 3,
    status TEXT NOT NULL DEFAULT 'queued',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    matched_room_id INTEGER REFERENCES rooms(id) ON DELETE SET NULL,
    UNIQUE(user_id, status)
);

CREATE TABLE IF NOT EXISTS user_stats (
    user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    games_played INTEGER NOT NULL DEFAULT 0,
    wins INTEGER NOT NULL DEFAULT 0,
    losses INTEGER NOT NULL DEFAULT 0,
    draws INTEGER NOT NULL DEFAULT 0,
    moves_made INTEGER NOT NULL DEFAULT 0,
    current_streak INTEGER NOT NULL DEFAULT 0,
    best_streak INTEGER NOT NULL DEFAULT 0,
    rating INTEGER NOT NULL DEFAULT 1000,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS achievements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    points INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS user_achievements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    achievement_id INTEGER NOT NULL REFERENCES achievements(id) ON DELETE CASCADE,
    unlocked_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, achievement_id)
);

CREATE TABLE IF NOT EXISTS game_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    game_id INTEGER NOT NULL REFERENCES games(id) ON DELETE CASCADE,
    event_type TEXT NOT NULL,
    payload TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_game_events_game ON game_events(game_id, id ASC);

CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    actor_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    action TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    entity_id INTEGER,
    payload TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_audit_action ON audit_log(action, created_at DESC);
"""


ACHIEVEMENTS = [
    ("first_win", "Первая победа", "Выиграть партию впервые.", 10),
    ("five_games", "Постоянный игрок", "Сыграть пять партий.", 15),
    ("win_streak_3", "Серия побед", "Выиграть три партии подряд.", 25),
    ("fast_finish", "Быстрая победа", "Выиграть партию за пять ходов или быстрее.", 20),
    ("large_board", "Большое поле", "Сыграть на поле больше 3x3.", 10),
]


def connect_db(path: str) -> sqlite3.Connection:
    if path != ":memory:":
        Path(path).parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path, detect_types=sqlite3.PARSE_DECLTYPES)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    return con


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        g.db = connect_db(current_app.config["DATABASE_PATH"])
    return g.db


def close_db(error: BaseException | None = None) -> None:
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db(app: Flask) -> None:
    with app.app_context():
        db = get_db()
        db.executescript(SCHEMA_SQL)
        seed_defaults(db)
        db.commit()


def seed_defaults(db: sqlite3.Connection) -> None:
    db.executemany(
        """
        INSERT OR IGNORE INTO achievements(code, title, description, points)
        VALUES (?, ?, ?, ?)
        """,
        ACHIEVEMENTS,
    )
    db.executemany(
        """
        UPDATE achievements
        SET title = ?, description = ?, points = ?
        WHERE code = ?
        """,
        [(title, description, points, code) for code, title, description, points in ACHIEVEMENTS],
    )


def fetch_one(query: str, params: Iterable[Any] = ()) -> sqlite3.Row | None:
    return get_db().execute(query, tuple(params)).fetchone()


def fetch_all(query: str, params: Iterable[Any] = ()) -> list[sqlite3.Row]:
    return list(get_db().execute(query, tuple(params)).fetchall())


def execute(query: str, params: Iterable[Any] = ()) -> sqlite3.Cursor:
    cur = get_db().execute(query, tuple(params))
    get_db().commit()
    return cur


def execute_many(query: str, params: Iterable[Iterable[Any]]) -> sqlite3.Cursor:
    cur = get_db().executemany(query, params)
    get_db().commit()
    return cur
