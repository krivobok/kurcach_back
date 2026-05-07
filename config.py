from __future__ import annotations

import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-me")
    DATABASE_PATH = os.environ.get("DATABASE_PATH", str(BASE_DIR / "instance" / "tictactoe.sqlite3"))
    TESTING = False
    JSON_SORT_KEYS = False
    MAX_CONTENT_LENGTH = 1024 * 1024
    TOKEN_TTL_SECONDS = 60 * 60 * 24 * 14
    DEFAULT_BOARD_SIZE = 3
    DEFAULT_WIN_LENGTH = 3
    DEFAULT_RATING = 1000
    MATCHMAKING_RATING_SPREAD = 250
    SOCKETIO_ASYNC_MODE = "threading"
    ADMIN_REGISTRATION_CODE = os.environ.get("ADMIN_REGISTRATION_CODE", "admin123")


class TestingConfig(Config):
    TESTING = True
    DATABASE_PATH = ":memory:"
    SECRET_KEY = "testing-secret"
    TOKEN_TTL_SECONDS = 60 * 60
    ADMIN_REGISTRATION_CODE = "admin-test-code"
