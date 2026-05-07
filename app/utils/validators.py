from __future__ import annotations

import re
from typing import Any


USERNAME_RE = re.compile(r"^[A-Za-z0-9_]{3,32}$")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class ValidationError(ValueError):
    def __init__(self, message: str, field: str | None = None) -> None:
        super().__init__(message)
        self.field = field


def require_json(data: Any) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise ValidationError("JSON object is required")
    return data


def required_str(data: dict[str, Any], field: str, min_len: int = 1, max_len: int = 255) -> str:
    value = data.get(field)
    if not isinstance(value, str):
        raise ValidationError(f"{field} must be a string", field)
    value = value.strip()
    if len(value) < min_len:
        raise ValidationError(f"{field} is too short", field)
    if len(value) > max_len:
        raise ValidationError(f"{field} is too long", field)
    return value


def optional_str(data: dict[str, Any], field: str, max_len: int = 255) -> str | None:
    value = data.get(field)
    if value is None or value == "":
        return None
    if not isinstance(value, str):
        raise ValidationError(f"{field} must be a string", field)
    value = value.strip()
    if len(value) > max_len:
        raise ValidationError(f"{field} is too long", field)
    return value


def int_range(data: dict[str, Any], field: str, default: int, min_value: int, max_value: int) -> int:
    value = data.get(field, default)
    try:
        value = int(value)
    except (TypeError, ValueError) as exc:
        raise ValidationError(f"{field} must be an integer", field) from exc
    if value < min_value or value > max_value:
        raise ValidationError(f"{field} must be between {min_value} and {max_value}", field)
    return value


def bool_value(data: dict[str, Any], field: str, default: bool = False) -> bool:
    value = data.get(field, default)
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        if value.lower() in {"true", "1", "yes"}:
            return True
        if value.lower() in {"false", "0", "no"}:
            return False
    raise ValidationError(f"{field} must be boolean", field)


def validate_username(username: str) -> str:
    if not USERNAME_RE.match(username):
        raise ValidationError("username must contain 3-32 latin letters, digits or underscores", "username")
    return username


def validate_email(email: str | None) -> str | None:
    if email is not None and not EMAIL_RE.match(email):
        raise ValidationError("email has invalid format", "email")
    return email


def validate_symbol(symbol: str) -> str:
    symbol = symbol.upper()
    if symbol not in {"X", "O"}:
        raise ValidationError("symbol must be X or O", "symbol")
    return symbol


def validate_game_config(board_size: int, win_length: int) -> tuple[int, int]:
    if win_length > board_size:
        raise ValidationError("win_length cannot be greater than board_size", "win_length")
    if board_size > 10:
        raise ValidationError("board_size cannot be greater than 10", "board_size")
    return board_size, win_length
