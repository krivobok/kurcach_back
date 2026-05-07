from __future__ import annotations

from typing import Any


def ref(name: str) -> dict[str, str]:
    return {"$ref": f"#/components/schemas/{name}"}


def success(schema: dict[str, Any] | None = None, description: str = "Успешный ответ") -> dict[str, Any]:
    payload: dict[str, Any] = {
        "description": description,
        "content": {
            "application/json": {
                "schema": {
                    "type": "object",
                    "required": ["ok"],
                    "properties": {
                        "ok": {"type": "boolean", "example": True},
                        "message": {"type": "string", "example": "OK"},
                    },
                }
            }
        },
    }
    if schema:
        payload["content"]["application/json"]["schema"]["properties"]["data"] = schema
    return payload


def error_response(description: str, code: str) -> dict[str, Any]:
    return {
        "description": description,
        "content": {
            "application/json": {
                "schema": ref("ApiError"),
                "examples": {
                    code: {
                        "summary": description,
                        "value": {"ok": False, "error": {"code": code, "message": description}},
                    }
                },
            }
        },
    }


def json_body(schema_name: str, description: str, example: dict[str, Any] | None = None) -> dict[str, Any]:
    body: dict[str, Any] = {
        "required": True,
        "description": description,
        "content": {"application/json": {"schema": ref(schema_name)}},
    }
    if example:
        body["content"]["application/json"]["example"] = example
    return body


def bearer() -> list[dict[str, list[str]]]:
    return [{"bearerAuth": []}]


def path_param(name: str, description: str) -> dict[str, Any]:
    return {
        "name": name,
        "in": "path",
        "required": True,
        "description": description,
        "schema": {"type": "integer", "minimum": 1},
        "example": 1,
    }


def limit_param(default: int = 20, maximum: int = 100) -> dict[str, Any]:
    return {
        "name": "limit",
        "in": "query",
        "required": False,
        "description": "Количество элементов в ответе.",
        "schema": {"type": "integer", "minimum": 1, "maximum": maximum, "default": default},
    }


def offset_param() -> dict[str, Any]:
    return {
        "name": "offset",
        "in": "query",
        "required": False,
        "description": "Смещение для постраничной навигации.",
        "schema": {"type": "integer", "minimum": 0, "default": 0},
    }


def build_openapi_spec() -> dict[str, Any]:
    return {
        "openapi": "3.0.3",
        "info": {
            "title": "Крестики-нолики: серверные запросы",
            "version": "1.0.0",
            "description": (
                "Подробная спецификация серверной части веб-приложения «Крестики-нолики». "
                "Сервер поддерживает регистрацию, авторизацию, комнаты, игровые ходы, чат, "
                "статистику, достижения, повтор партии, матчмейкинг и административный аудит. "
                "Для защищенных запросов используется токен доступа из ответа входа или регистрации."
            ),
            "license": {"name": "Учебный курсовой проект"},
        },
        "servers": [
            {"url": "http://127.0.0.1:5000", "description": "Локальный сервер разработки"},
            {"url": "http://localhost:5000", "description": "Альтернативный локальный адрес"},
        ],
        "tags": [
            {"name": "Система", "description": "Проверка состояния сервера и машинная документация."},
            {"name": "Авторизация", "description": "Регистрация, вход, выход и текущий профиль."},
            {"name": "Пользователи", "description": "Пользователи, поиск и личная статистика."},
            {"name": "Комнаты", "description": "Создание комнат, вход, готовность и реванш."},
            {"name": "Чат", "description": "История сообщений и отправка чата комнаты."},
            {"name": "Игры", "description": "Состояние партии, ходы, игру с компьютером, подсказки, сдача и повтор партии."},
            {"name": "Подбор соперника", "description": "Автоматический подбор соперника."},
            {"name": "Статистика", "description": "Рейтинг и глобальная статистика проекта."},
            {"name": "Администрирование", "description": "Административные запросы."},
        ],
        "paths": build_paths(),
        "components": build_components(),
        "x-websocket-events": websocket_events(),
    }


def build_components() -> dict[str, Any]:
    return {
        "securitySchemes": {
            "bearerAuth": {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "token",
                "description": "Токен из поля data.token в ответах /api/auth/register и /api/auth/login.",
            }
        },
        "schemas": {
            "ApiError": {
                "type": "object",
                "required": ["ok", "error"],
                "properties": {
                    "ok": {"type": "boolean", "example": False},
                    "error": {
                        "type": "object",
                        "required": ["code", "message"],
                        "properties": {
                            "code": {"type": "string", "example": "validation_error"},
                            "message": {"type": "string", "example": "username must contain 3-32 latin letters, digits or underscores"},
                            "details": {"type": "object", "additionalProperties": True},
                        },
                    },
                },
            },
            "RegisterRequest": {
                "type": "object",
                "required": ["username", "password"],
                "properties": {
                    "username": {"type": "string", "minLength": 3, "maxLength": 32, "pattern": "^[A-Za-z0-9_]+$", "example": "player_one"},
                    "password": {"type": "string", "minLength": 6, "maxLength": 128, "format": "password", "example": "secret123"},
                    "display_name": {"type": "string", "maxLength": 80, "example": "Игрок 1"},
                    "email": {"type": "string", "format": "email", "nullable": True, "example": "player@example.com"},
                    "avatar_url": {"type": "string", "nullable": True, "example": "https://example.com/avatar.png"},
                    "account_type": {"type": "string", "enum": ["client", "admin"], "default": "client", "example": "client"},
                    "admin_code": {"type": "string", "nullable": True, "description": "Нужен только для account_type=admin.", "example": "admin123"},
                },
            },
            "LoginRequest": {
                "type": "object",
                "required": ["username", "password"],
                "properties": {
                    "username": {"type": "string", "example": "player_one"},
                    "password": {"type": "string", "format": "password", "example": "secret123"},
                },
            },
            "ProfileUpdateRequest": {
                "type": "object",
                "properties": {
                    "display_name": {"type": "string", "maxLength": 80, "example": "Новый ник"},
                    "email": {"type": "string", "format": "email", "nullable": True, "example": "new@example.com"},
                    "avatar_url": {"type": "string", "nullable": True, "example": "https://example.com/new-avatar.png"},
                },
            },
            "AuthSession": {
                "type": "object",
                "required": ["token", "expires_at", "user"],
                "properties": {
                    "token": {"type": "string", "example": "8KpW9kQZbP-token-example"},
                    "expires_at": {"type": "string", "format": "date-time"},
                    "user": ref("User"),
                },
            },
            "User": {
                "type": "object",
                "required": ["id", "username", "display_name", "status", "rating", "created_at", "is_admin"],
                "properties": {
                    "id": {"type": "integer", "example": 1},
                    "username": {"type": "string", "example": "player_one"},
                    "display_name": {"type": "string", "example": "Игрок 1"},
                    "email": {"type": "string", "nullable": True, "example": "player@example.com"},
                    "avatar_url": {"type": "string", "nullable": True},
                    "status": {"type": "string", "enum": ["online", "offline", "banned"], "example": "online"},
                    "rating": {"type": "integer", "example": 1024},
                    "created_at": {"type": "string", "format": "date-time"},
                    "last_seen_at": {"type": "string", "format": "date-time", "nullable": True},
                    "is_admin": {"type": "boolean", "example": False},
                },
            },
            "RoomCreateRequest": {
                "type": "object",
                "required": ["name"],
                "properties": {
                    "name": {"type": "string", "minLength": 1, "maxLength": 80, "example": "Комната игрока"},
                    "mode": {"type": "string", "enum": ["public", "private", "ai", "matchmaking"], "default": "public", "example": "ai"},
                    "board_size": {"type": "integer", "minimum": 3, "maximum": 10, "default": 3, "example": 3},
                    "win_length": {"type": "integer", "minimum": 3, "maximum": 10, "default": 3, "example": 3},
                    "symbol": {"type": "string", "enum": ["X", "O"], "default": "X", "example": "X"},
                    "ready": {"type": "boolean", "default": True, "example": True},
                },
            },
            "RoomJoinRequest": {
                "type": "object",
                "properties": {
                    "symbol": {"type": "string", "enum": ["X", "O"], "nullable": True, "example": "O"},
                    "ready": {"type": "boolean", "default": True, "example": True},
                },
            },
            "ReadyRequest": {
                "type": "object",
                "required": ["ready"],
                "properties": {"ready": {"type": "boolean", "example": True}},
            },
            "RoomPlayer": {
                "type": "object",
                "properties": {
                    "id": {"type": "integer", "example": 1},
                    "room_id": {"type": "integer", "example": 1},
                    "user_id": {"type": "integer", "example": 1},
                    "symbol": {"type": "string", "enum": ["X", "O"], "example": "X"},
                    "seat": {"type": "integer", "example": 1},
                    "joined_at": {"type": "string", "format": "date-time"},
                    "left_at": {"type": "string", "format": "date-time", "nullable": True},
                    "is_ready": {"type": "integer", "enum": [0, 1], "example": 1},
                    "username": {"type": "string", "example": "player_one"},
                    "display_name": {"type": "string", "example": "Игрок 1"},
                    "rating": {"type": "integer", "example": 1000},
                },
            },
            "Room": {
                "type": "object",
                "properties": {
                    "id": {"type": "integer", "example": 1},
                    "slug": {"type": "string", "example": "room-a1b2c3d4"},
                    "name": {"type": "string", "example": "Комната игрока"},
                    "mode": {"type": "string", "enum": ["public", "private", "ai", "matchmaking"]},
                    "status": {"type": "string", "enum": ["waiting", "playing", "finished", "closed"]},
                    "board_size": {"type": "integer", "example": 3},
                    "win_length": {"type": "integer", "example": 3},
                    "max_players": {"type": "integer", "example": 2},
                    "created_by": {"type": "integer", "nullable": True},
                    "current_game_id": {"type": "integer", "nullable": True},
                    "created_at": {"type": "string", "format": "date-time"},
                    "updated_at": {"type": "string", "format": "date-time"},
                    "players": {"type": "array", "items": ref("RoomPlayer")},
                    "game": {"nullable": True, "allOf": [ref("Game")]},
                },
            },
            "Game": {
                "type": "object",
                "properties": {
                    "id": {"type": "integer", "example": 1},
                    "room_id": {"type": "integer", "example": 1},
                    "status": {"type": "string", "enum": ["waiting", "playing", "finished"], "example": "playing"},
                    "board_size": {"type": "integer", "example": 3},
                    "win_length": {"type": "integer", "example": 3},
                    "player_x_id": {"type": "integer", "nullable": True, "example": 1},
                    "player_o_id": {"type": "integer", "nullable": True, "example": 2},
                    "current_turn": {"type": "string", "enum": ["X", "O"], "example": "X"},
                    "winner_symbol": {"type": "string", "enum": ["X", "O"], "nullable": True},
                    "winner_user_id": {"type": "integer", "nullable": True},
                    "draw": {"type": "boolean", "example": False},
                    "winning_line": {"type": "array", "items": {"type": "array", "items": {"type": "integer"}}, "example": [[0, 0], [0, 1], [0, 2]]},
                    "move_count": {"type": "integer", "example": 2},
                    "started_at": {"type": "string", "format": "date-time", "nullable": True},
                    "finished_at": {"type": "string", "format": "date-time", "nullable": True},
                    "created_at": {"type": "string", "format": "date-time"},
                    "board": ref("Board"),
                    "available_moves": {"type": "array", "items": ref("CellCoordinate")},
                },
            },
            "Board": {
                "type": "array",
                "description": "Двумерный массив клеток. Пустая клетка возвращается пустой строкой.",
                "items": {"type": "array", "items": {"type": "string", "enum": ["", "X", "O"]}},
                "example": [["X", "", ""], ["", "O", ""], ["", "", ""]],
            },
            "CellCoordinate": {
                "type": "array",
                "minItems": 2,
                "maxItems": 2,
                "items": {"type": "integer"},
                "example": [0, 2],
            },
            "MoveRequest": {
                "type": "object",
                "required": ["row", "col"],
                "properties": {
                    "row": {"type": "integer", "minimum": 0, "maximum": 9, "example": 0},
                    "col": {"type": "integer", "minimum": 0, "maximum": 9, "example": 0},
                },
            },
            "Move": {
                "type": "object",
                "properties": {
                    "id": {"type": "integer", "example": 1},
                    "game_id": {"type": "integer", "example": 1},
                    "user_id": {"type": "integer", "nullable": True, "example": 1},
                    "symbol": {"type": "string", "enum": ["X", "O"], "example": "X"},
                    "row": {"type": "integer", "example": 0},
                    "col": {"type": "integer", "example": 0},
                    "move_number": {"type": "integer", "example": 1},
                    "board_after": {"type": "string", "example": "[[\"X\",null,null],[null,null,null],[null,null,null]]"},
                    "created_at": {"type": "string", "format": "date-time"},
                },
            },
            "MoveResult": {
                "type": "object",
                "properties": {
                    "game": ref("Game"),
                    "move": ref("Move"),
                    "board": ref("Board"),
                    "source": {"type": "string", "enum": ["player", "ai"], "example": "player"},
                    "ai_move": ref("Move"),
                    "achievements": {"type": "array", "items": {"type": "object", "additionalProperties": True}},
                },
            },
            "AiMoveRequest": {
                "type": "object",
                "properties": {"difficulty": {"type": "string", "enum": ["easy", "medium", "hard"], "default": "hard", "example": "hard"}},
            },
            "Hint": {
                "type": "object",
                "properties": {
                    "best": ref("MoveScore"),
                    "top_moves": {"type": "array", "items": ref("MoveScore")},
                },
            },
            "GameAnalysis": {
                "type": "object",
                "description": "Серверный анализ текущей позиции: лучший ход, угрозы, потенциал линий и рекомендация.",
                "properties": {
                    "game": ref("Game"),
                    "board_status": {"type": "string", "enum": ["playing", "win", "draw"], "example": "playing"},
                    "winner": {"type": "string", "nullable": True, "example": None},
                    "current_symbol": {"type": "string", "enum": ["X", "O"], "example": "X"},
                    "opponent_symbol": {"type": "string", "enum": ["X", "O"], "example": "O"},
                    "actor_symbol": {"type": "string", "enum": ["X", "O"], "nullable": True, "example": "X"},
                    "is_actor_turn": {"type": "boolean", "example": True},
                    "available_moves_count": {"type": "integer", "example": 6},
                    "filled_cells_count": {"type": "integer", "example": 3},
                    "progress_percent": {"type": "number", "format": "float", "example": 33.33},
                    "best_move": ref("MoveScore"),
                    "top_moves": {"type": "array", "items": ref("MoveScore")},
                    "winning_moves": {"type": "object", "additionalProperties": {"type": "array", "items": ref("AnalysisMove")}},
                    "immediate_threats": {"type": "array", "items": ref("AnalysisMove")},
                    "risk_level": {"type": "string", "enum": ["winning", "danger", "normal", "finished"], "example": "normal"},
                    "recommendation": {"type": "string", "example": "Лучший ход по оценке сервера: строка 1, столбец 1."},
                    "line_potential": {"type": "object", "additionalProperties": ref("LinePotential")},
                    "strategic_zones": {"type": "object", "additionalProperties": True},
                },
            },
            "AnalysisMove": {
                "type": "object",
                "properties": {
                    "row": {"type": "integer", "example": 0},
                    "col": {"type": "integer", "example": 2},
                    "line": {"type": "array", "items": ref("CellCoordinate")},
                },
            },
            "LinePotential": {
                "type": "object",
                "properties": {
                    "open_lines": {"type": "integer", "example": 5},
                    "strongest_line": {"type": "integer", "example": 2},
                    "one_move_to_win": {"type": "integer", "example": 1},
                    "fork_cells": {"type": "array", "items": {"type": "object", "additionalProperties": True}},
                },
            },
            "MoveScore": {
                "type": "object",
                "properties": {
                    "row": {"type": "integer", "example": 0},
                    "col": {"type": "integer", "example": 2},
                    "score": {"type": "integer", "example": 10000},
                    "reason": {"type": "string", "example": "winning_move"},
                },
            },
            "ChatMessageRequest": {
                "type": "object",
                "required": ["body"],
                "properties": {"body": {"type": "string", "minLength": 1, "maxLength": 500, "example": "Привет, хорошей игры!"}},
            },
            "ChatMessage": {
                "type": "object",
                "properties": {
                    "id": {"type": "integer", "example": 1},
                    "room_id": {"type": "integer", "example": 1},
                    "user_id": {"type": "integer", "nullable": True, "example": 1},
                    "body": {"type": "string", "example": "Привет!"},
                    "kind": {"type": "string", "example": "user"},
                    "created_at": {"type": "string", "format": "date-time"},
                },
            },
            "Replay": {
                "type": "object",
                "properties": {
                    "game": ref("Game"),
                    "states": {"type": "array", "items": ref("ReplayState")},
                    "events": {"type": "array", "items": ref("GameEvent")},
                },
            },
            "ReplayState": {
                "type": "object",
                "properties": {
                    "move_number": {"type": "integer", "example": 3},
                    "board": ref("Board"),
                    "symbol": {"type": "string", "nullable": True, "example": "X"},
                    "row": {"type": "integer", "example": 0},
                    "col": {"type": "integer", "example": 2},
                },
            },
            "GameEvent": {
                "type": "object",
                "properties": {
                    "id": {"type": "integer"},
                    "game_id": {"type": "integer"},
                    "event_type": {"type": "string", "example": "move"},
                    "payload": {"type": "object", "additionalProperties": True},
                    "created_at": {"type": "string", "format": "date-time"},
                },
            },
            "MatchmakingRequest": {
                "type": "object",
                "properties": {
                    "board_size": {"type": "integer", "minimum": 3, "maximum": 10, "default": 3, "example": 3},
                    "win_length": {"type": "integer", "minimum": 3, "maximum": 10, "default": 3, "example": 3},
                },
            },
            "MatchmakingResult": {
                "type": "object",
                "properties": {
                    "matched": {"type": "boolean", "example": False},
                    "queue": {"type": "object", "additionalProperties": True},
                    "room": ref("Room"),
                    "cancelled": {"type": "boolean", "example": True},
                },
            },
            "PlayerStats": {
                "type": "object",
                "properties": {
                    "user_id": {"type": "integer", "example": 1},
                    "games_played": {"type": "integer", "example": 10},
                    "wins": {"type": "integer", "example": 6},
                    "losses": {"type": "integer", "example": 3},
                    "draws": {"type": "integer", "example": 1},
                    "moves_made": {"type": "integer", "example": 42},
                    "current_streak": {"type": "integer", "example": 2},
                    "best_streak": {"type": "integer", "example": 4},
                    "rating": {"type": "integer", "example": 1108},
                    "win_rate": {"type": "number", "format": "float", "example": 0.6},
                    "loss_rate": {"type": "number", "format": "float", "example": 0.3},
                    "draw_rate": {"type": "number", "format": "float", "example": 0.1},
                    "updated_at": {"type": "string", "format": "date-time"},
                },
            },
            "Achievement": {
                "type": "object",
                "properties": {
                    "id": {"type": "integer", "example": 1},
                    "code": {"type": "string", "example": "first_win"},
                    "title": {"type": "string", "example": "Первая победа"},
                    "description": {"type": "string", "example": "Выиграть партию впервые."},
                    "points": {"type": "integer", "example": 10},
                },
            },
            "AchievementCatalogEntry": {
                "allOf": [
                    ref("Achievement"),
                    {
                        "type": "object",
                        "properties": {"unlocked_count": {"type": "integer", "example": 3}},
                    },
                ]
            },
            "UserDashboard": {
                "type": "object",
                "properties": {
                    "user": ref("User"),
                    "stats": ref("PlayerStats"),
                    "achievements": {"type": "array", "items": ref("Achievement")},
                    "recent_games": {"type": "array", "items": ref("RecentGame")},
                },
            },
            "RecentGame": {
                "allOf": [
                    ref("Game"),
                    {
                        "type": "object",
                        "properties": {
                            "room_name": {"type": "string", "example": "Комната игрока"},
                            "room_mode": {"type": "string", "example": "public"},
                            "room_status": {"type": "string", "example": "finished"},
                            "player_x_username": {"type": "string", "nullable": True, "example": "player_one"},
                            "player_o_username": {"type": "string", "nullable": True, "example": "player_two"},
                            "result_for_user": {"type": "string", "enum": ["win", "loss", "draw", "in_progress", "unknown"], "example": "win"},
                            "opponent_username": {"type": "string", "example": "player_two"},
                        },
                    },
                ]
            },
            "LeaderboardEntry": {
                "allOf": [
                    ref("PlayerStats"),
                    {
                        "type": "object",
                        "properties": {
                            "username": {"type": "string", "example": "player_one"},
                            "display_name": {"type": "string", "example": "Игрок 1"},
                            "avatar_url": {"type": "string", "nullable": True},
                        },
                    },
                ]
            },
            "Summary": {
                "type": "object",
                "properties": {
                    "rooms_total": {"type": "integer", "example": 5},
                    "rooms_waiting": {"type": "integer", "example": 1},
                    "rooms_playing": {"type": "integer", "example": 2},
                    "games_total": {"type": "integer", "example": 8},
                    "games_finished": {"type": "integer", "example": 6},
                    "draws": {"type": "integer", "example": 1},
                },
            },
            "AuditLog": {
                "type": "object",
                "properties": {
                    "id": {"type": "integer", "example": 1},
                    "actor_id": {"type": "integer", "nullable": True, "example": 1},
                    "action": {"type": "string", "example": "create_room"},
                    "entity_type": {"type": "string", "example": "room"},
                    "entity_id": {"type": "integer", "nullable": True, "example": 1},
                    "payload": {"type": "object", "additionalProperties": True},
                    "created_at": {"type": "string", "format": "date-time"},
                },
            },
            "AdminDashboard": {
                "type": "object",
                "properties": {
                    "users_total": {"type": "integer", "example": 12},
                    "rooms_total": {"type": "integer", "example": 5},
                    "rooms_waiting": {"type": "integer", "example": 1},
                    "rooms_playing": {"type": "integer", "example": 2},
                    "rooms_finished": {"type": "integer", "example": 2},
                    "rooms_closed": {"type": "integer", "example": 1},
                    "games_total": {"type": "integer", "example": 18},
                    "games_playing": {"type": "integer", "example": 2},
                    "games_finished": {"type": "integer", "example": 16},
                    "latest_audit": {"type": "array", "items": ref("AuditLog")},
                },
            },
            "AdminUser": {
                "allOf": [
                    ref("User"),
                    {
                        "type": "object",
                        "properties": {
                            "role": {"type": "string", "enum": ["client", "admin"], "example": "client"},
                            "games_played": {"type": "integer", "example": 3},
                            "wins": {"type": "integer", "example": 1},
                            "losses": {"type": "integer", "example": 1},
                            "draws": {"type": "integer", "example": 1},
                            "moves_made": {"type": "integer", "example": 12},
                            "revoked_tokens": {"type": "integer", "example": 0},
                        },
                    },
                ]
            },
            "RoleUpdateRequest": {
                "type": "object",
                "required": ["is_admin"],
                "properties": {"is_admin": {"type": "boolean", "example": True}},
            },
            "UserStatusUpdateRequest": {
                "type": "object",
                "required": ["status"],
                "properties": {"status": {"type": "string", "enum": ["online", "offline", "banned"], "example": "banned"}},
            },
            "RoomStatusUpdateRequest": {
                "type": "object",
                "required": ["status"],
                "properties": {"status": {"type": "string", "enum": ["waiting", "playing", "finished", "closed"], "example": "closed"}},
            },
            "Health": {
                "type": "object",
                "properties": {
                    "service": {"type": "string", "example": "tic-tac-toe-backend"},
                    "status": {"type": "string", "example": "ok"},
                },
            },
        },
    }


def build_paths() -> dict[str, Any]:
    return {
        "/api/health": {
            "get": {
                "tags": ["Система"],
                "summary": "Проверить состояние сервера",
                "description": "Возвращает короткий health-check без авторизации.",
                "responses": {"200": success(ref("Health"))},
            }
        },
        "/api/openapi.json": {
            "get": {
                "tags": ["Система"],
                "summary": "Получить OpenAPI спецификацию",
                "description": "Машинно-читаемый Swagger/OpenAPI документ для импорта в Swagger UI, Postman или Insomnia.",
                "responses": {"200": {"description": "OpenAPI JSON"}},
            }
        },
        "/api/postman.json": {
            "get": {
                "tags": ["Система"],
                "summary": "Получить Postman collection",
                "description": "Готовая коллекция Postman v2.1 с примерами запросов и автосохранением переменных.",
                "responses": {"200": {"description": "Postman collection JSON"}},
            }
        },
        "/api/auth/register": {
            "post": {
                "tags": ["Авторизация"],
                "summary": "Зарегистрировать пользователя",
                "description": "Создает пользователя, начальную статистику и возвращает токен доступа.",
                "requestBody": json_body("RegisterRequest", "Данные нового пользователя. Для администратора передайте account_type=admin и admin_code.", {"username": "player_one", "password": "secret123", "display_name": "Игрок 1", "account_type": "client"}),
                "responses": {"201": success(ref("AuthSession"), "Пользователь зарегистрирован"), "400": error_response("Ошибка регистрации", "auth_error"), "422": error_response("Ошибка валидации", "validation_error")},
            }
        },
        "/api/auth/login": {
            "post": {
                "tags": ["Авторизация"],
                "summary": "Войти в аккаунт",
                "description": "Проверяет пароль, переводит пользователя online и возвращает новый токен доступа.",
                "requestBody": json_body("LoginRequest", "Логин и пароль", {"username": "player_one", "password": "secret123"}),
                "responses": {"200": success(ref("AuthSession"), "Вход выполнен"), "400": error_response("Неверный логин или пароль", "auth_error")},
            }
        },
        "/api/auth/logout": {
            "post": {
                "tags": ["Авторизация"],
                "summary": "Выйти из аккаунта",
                "description": "Отзывает текущий токен доступа.",
                "security": bearer(),
                "responses": {"200": success({"type": "object", "properties": {"revoked": {"type": "boolean", "example": True}}}), "401": error_response("Authentication required", "auth_required")},
            }
        },
        "/api/auth/me": {
            "get": {
                "tags": ["Авторизация"],
                "summary": "Получить текущего пользователя",
                "security": bearer(),
                "responses": {"200": success(ref("User")), "401": error_response("Authentication required", "auth_required")},
            },
            "patch": {
                "tags": ["Авторизация"],
                "summary": "Обновить профиль",
                "security": bearer(),
                "requestBody": json_body("ProfileUpdateRequest", "Поля профиля для изменения", {"display_name": "Новый ник", "email": "new@example.com"}),
                "responses": {"200": success(ref("User")), "401": error_response("Authentication required", "auth_required"), "422": error_response("Ошибка валидации", "validation_error")},
            },
        },
        "/api/users": {
            "get": {
                "tags": ["Пользователи"],
                "summary": "Список или поиск пользователей",
                "description": "Без q возвращает последних пользователей, с q ищет по username, display_name и email.",
                "security": bearer(),
                "parameters": [
                    {"name": "q", "in": "query", "required": False, "schema": {"type": "string"}, "description": "Поисковая строка.", "example": "player"},
                    limit_param(20, 100),
                    offset_param(),
                ],
                "responses": {"200": success({"type": "array", "items": ref("User")}), "401": error_response("Authentication required", "auth_required")},
            }
        },
        "/api/users/{user_id}": {
            "get": {
                "tags": ["Пользователи"],
                "summary": "Профиль, статистика и достижения пользователя",
                "security": bearer(),
                "parameters": [path_param("user_id", "ID пользователя")],
                "responses": {"200": success(ref("UserDashboard")), "401": error_response("Authentication required", "auth_required"), "404": error_response("User not found", "not_found")},
            }
        },
        "/api/users/{user_id}/games": {
            "get": {
                "tags": ["Пользователи"],
                "summary": "История партий пользователя",
                "description": "Последние партии выбранного пользователя с результатом относительно этого пользователя.",
                "security": bearer(),
                "parameters": [path_param("user_id", "ID пользователя"), limit_param(10, 50)],
                "responses": {"200": success({"type": "array", "items": ref("RecentGame")}), "401": error_response("Authentication required", "auth_required"), "404": error_response("User not found", "not_found")},
            }
        },
        "/api/rooms": {
            "get": {
                "tags": ["Комнаты"],
                "summary": "Получить список комнат",
                "parameters": [
                    {"name": "status", "in": "query", "required": False, "description": "Фильтр по статусу комнаты.", "schema": {"type": "string", "enum": ["waiting", "playing", "finished"]}},
                    limit_param(30, 100),
                    offset_param(),
                ],
                "responses": {"200": success({"type": "array", "items": ref("Room")})},
            },
            "post": {
                "tags": ["Комнаты"],
                "summary": "Создать комнату",
                "description": "Создает комнату и сразу добавляет текущего пользователя. Для mode=ai сразу стартует партия против компьютера.",
                "security": bearer(),
                "requestBody": json_body("RoomCreateRequest", "Параметры комнаты", {"name": "Моя комната", "mode": "ai", "board_size": 3, "win_length": 3, "symbol": "X"}),
                "responses": {"201": success(ref("Room"), "Комната создана"), "401": error_response("Authentication required", "auth_required"), "422": error_response("Ошибка валидации", "validation_error")},
            },
        },
        "/api/rooms/{room_id}": {
            "get": {
                "tags": ["Комнаты"],
                "summary": "Получить состояние комнаты",
                "parameters": [path_param("room_id", "ID комнаты")],
                "responses": {"200": success(ref("Room")), "404": error_response("Room not found", "not_found")},
            }
        },
        "/api/rooms/{room_id}/join": {
            "post": {
                "tags": ["Комнаты"],
                "summary": "Присоединиться к комнате",
                "description": "Добавляет текущего пользователя вторым игроком. Если оба игрока готовы, стартует игра.",
                "security": bearer(),
                "parameters": [path_param("room_id", "ID комнаты")],
                "requestBody": json_body("RoomJoinRequest", "Знак и готовность игрока", {"symbol": "O", "ready": True}),
                "responses": {"200": success(ref("Room")), "401": error_response("Authentication required", "auth_required"), "409": error_response("Room is full", "conflict")},
            }
        },
        "/api/rooms/{room_id}/leave": {
            "post": {
                "tags": ["Комнаты"],
                "summary": "Покинуть комнату",
                "security": bearer(),
                "parameters": [path_param("room_id", "ID комнаты")],
                "responses": {"200": success(ref("Room")), "401": error_response("Authentication required", "auth_required")},
            }
        },
        "/api/rooms/{room_id}/ready": {
            "patch": {
                "tags": ["Комнаты"],
                "summary": "Изменить готовность игрока",
                "security": bearer(),
                "parameters": [path_param("room_id", "ID комнаты")],
                "requestBody": json_body("ReadyRequest", "Готовность игрока", {"ready": True}),
                "responses": {"200": success(ref("Room")), "401": error_response("Authentication required", "auth_required")},
            }
        },
        "/api/rooms/{room_id}/chat": {
            "get": {
                "tags": ["Чат"],
                "summary": "История чата комнаты",
                "parameters": [path_param("room_id", "ID комнаты"), limit_param(50, 100)],
                "responses": {"200": success({"type": "array", "items": ref("ChatMessage")}), "404": error_response("Room not found", "not_found")},
            },
            "post": {
                "tags": ["Чат"],
                "summary": "Отправить сообщение в чат",
                "security": bearer(),
                "parameters": [path_param("room_id", "ID комнаты")],
                "requestBody": json_body("ChatMessageRequest", "Текст сообщения", {"body": "Привет, хорошей игры!"}),
                "responses": {"201": success(ref("ChatMessage")), "401": error_response("Authentication required", "auth_required"), "403": error_response("Only room players can write to room chat", "game_error")},
            },
        },
        "/api/rooms/{room_id}/rematch": {
            "post": {
                "tags": ["Комнаты"],
                "summary": "Начать реванш",
                "security": bearer(),
                "parameters": [path_param("room_id", "ID комнаты")],
                "responses": {"200": success(ref("Room")), "401": error_response("Authentication required", "auth_required")},
            }
        },
        "/api/games/{game_id}": {
            "get": {
                "tags": ["Игры"],
                "summary": "Получить состояние игры",
                "parameters": [path_param("game_id", "ID игры")],
                "responses": {"200": success(ref("Game")), "404": error_response("Game not found", "not_found")},
            }
        },
        "/api/games/{game_id}/moves": {
            "post": {
                "tags": ["Игры"],
                "summary": "Сделать ход",
                "description": "Ход текущего игрока. Для AI-комнаты сервер автоматически делает ответный ход компьютера.",
                "security": bearer(),
                "parameters": [path_param("game_id", "ID игры")],
                "requestBody": json_body("MoveRequest", "Координаты клетки, начиная с нуля", {"row": 0, "col": 0}),
                "responses": {"201": success(ref("MoveResult")), "401": error_response("Authentication required", "auth_required"), "403": error_response("User does not play this game", "game_error")},
            }
        },
        "/api/games/{game_id}/ai-move": {
            "post": {
                "tags": ["Игры"],
                "summary": "Принудительный ход AI",
                "description": "Используется для AI-игры или тестирования. Делает ход за текущий символ.",
                "security": bearer(),
                "parameters": [path_param("game_id", "ID игры")],
                "requestBody": json_body("AiMoveRequest", "Сложность AI", {"difficulty": "hard"}),
                "responses": {"201": success(ref("MoveResult")), "401": error_response("Authentication required", "auth_required")},
            }
        },
        "/api/games/{game_id}/hint": {
            "get": {
                "tags": ["Игры"],
                "summary": "Получить подсказку лучшего хода",
                "security": bearer(),
                "parameters": [
                    path_param("game_id", "ID игры"),
                    {"name": "difficulty", "in": "query", "required": False, "schema": {"type": "string", "enum": ["easy", "medium", "hard"], "default": "hard"}},
                ],
                "responses": {"200": success(ref("Hint")), "401": error_response("Authentication required", "auth_required")},
            }
        },
        "/api/games/{game_id}/analysis": {
            "get": {
                "tags": ["Игры"],
                "summary": "Серверный анализ позиции",
                "description": "Показывает лучший ход, немедленные угрозы, потенциал линий, процент заполнения поля и текстовую рекомендацию.",
                "parameters": [
                    path_param("game_id", "ID игры"),
                    {"name": "difficulty", "in": "query", "required": False, "schema": {"type": "string", "enum": ["easy", "medium", "hard"], "default": "hard"}},
                ],
                "responses": {"200": success(ref("GameAnalysis")), "404": error_response("Game not found", "not_found")},
            }
        },
        "/api/games/{game_id}/surrender": {
            "post": {
                "tags": ["Игры"],
                "summary": "Сдаться",
                "security": bearer(),
                "parameters": [path_param("game_id", "ID игры")],
                "responses": {"200": success(ref("Game")), "401": error_response("Authentication required", "auth_required")},
            }
        },
        "/api/games/{game_id}/повтор партии": {
            "get": {
                "tags": ["Игры"],
                "summary": "Replay партии",
                "description": "Возвращает все состояния доски после каждого хода и список игровых событий.",
                "parameters": [path_param("game_id", "ID игры")],
                "responses": {"200": success(ref("Replay")), "404": error_response("Game not found", "not_found")},
            }
        },
        "/api/matchmaking": {
            "post": {
                "tags": ["Подбор соперника"],
                "summary": "Встать в очередь матчмейкинга",
                "security": bearer(),
                "requestBody": json_body("MatchmakingRequest", "Параметры поля для подбора", {"board_size": 3, "win_length": 3}),
                "responses": {"200": success(ref("MatchmakingResult")), "401": error_response("Authentication required", "auth_required")},
            },
            "delete": {
                "tags": ["Подбор соперника"],
                "summary": "Отменить матчмейкинг",
                "security": bearer(),
                "responses": {"200": success(ref("MatchmakingResult")), "401": error_response("Authentication required", "auth_required")},
            },
        },
        "/api/leaderboard": {
            "get": {
                "tags": ["Статистика"],
                "summary": "Рейтинг игроков",
                "parameters": [limit_param(20, 100)],
                "responses": {"200": success({"type": "array", "items": ref("LeaderboardEntry")})},
            }
        },
        "/api/stats/me": {
            "get": {
                "tags": ["Статистика"],
                "summary": "Статистика текущего пользователя",
                "security": bearer(),
                "responses": {"200": success(ref("UserDashboard")), "401": error_response("Authentication required", "auth_required")},
            }
        },
        "/api/stats/achievements": {
            "get": {
                "tags": ["Статистика"],
                "summary": "Каталог достижений",
                "description": "Список всех достижений проекта с количеством пользователей, которые уже получили каждое достижение.",
                "responses": {"200": success({"type": "array", "items": ref("AchievementCatalogEntry")})},
            }
        },
        "/api/stats/summary": {
            "get": {
                "tags": ["Статистика"],
                "summary": "Глобальная статистика проекта",
                "responses": {"200": success(ref("Summary"))},
            }
        },
        "/api/admin/dashboard": {
            "get": {
                "tags": ["Администрирование"],
                "summary": "Админская сводка",
                "description": "Количество пользователей, комнат, игр и последние записи audit log.",
                "security": bearer(),
                "responses": {"200": success(ref("AdminDashboard")), "403": error_response("Admin access required", "admin_required")},
            }
        },
        "/api/admin/users": {
            "get": {
                "tags": ["Администрирование"],
                "summary": "Список пользователей для админа",
                "description": "Возвращает пользователей вместе с ролью, статусом и краткой статистикой.",
                "security": bearer(),
                "parameters": [
                    {"name": "q", "in": "query", "required": False, "schema": {"type": "string"}, "description": "Поиск по username, display_name или email."},
                    limit_param(50, 200),
                    offset_param(),
                ],
                "responses": {"200": success({"type": "array", "items": ref("AdminUser")}), "403": error_response("Admin access required", "admin_required")},
            }
        },
        "/api/admin/users/{user_id}": {
            "get": {
                "tags": ["Администрирование"],
                "summary": "Подробная карточка пользователя",
                "security": bearer(),
                "parameters": [path_param("user_id", "ID пользователя")],
                "responses": {"200": success(ref("UserDashboard")), "404": error_response("User not found", "not_found")},
            },
            "delete": {
                "tags": ["Администрирование"],
                "summary": "Удалить пользователя",
                "description": "Администратор не может удалить собственный аккаунт.",
                "security": bearer(),
                "parameters": [path_param("user_id", "ID пользователя")],
                "responses": {"200": success({"type": "object", "properties": {"deleted": {"type": "boolean"}, "user_id": {"type": "integer"}}}), "403": error_response("Admin access required", "admin_required")},
            },
        },
        "/api/admin/users/{user_id}/role": {
            "patch": {
                "tags": ["Администрирование"],
                "summary": "Выдать или забрать роль администратора",
                "security": bearer(),
                "parameters": [path_param("user_id", "ID пользователя")],
                "requestBody": json_body("RoleUpdateRequest", "Новая роль", {"is_admin": True}),
                "responses": {"200": success(ref("AdminUser")), "403": error_response("Admin access required", "admin_required")},
            }
        },
        "/api/admin/users/{user_id}/status": {
            "patch": {
                "tags": ["Администрирование"],
                "summary": "Изменить статус пользователя",
                "description": "Статус banned блокирует вход и отзывает активные токены пользователя.",
                "security": bearer(),
                "parameters": [path_param("user_id", "ID пользователя")],
                "requestBody": json_body("UserStatusUpdateRequest", "Новый статус", {"status": "banned"}),
                "responses": {"200": success(ref("AdminUser")), "403": error_response("Admin access required", "admin_required")},
            }
        },
        "/api/admin/users/{user_id}/tokens/revoke": {
            "post": {
                "tags": ["Администрирование"],
                "summary": "Отозвать все токены пользователя",
                "security": bearer(),
                "parameters": [path_param("user_id", "ID пользователя")],
                "responses": {"200": success({"type": "object", "properties": {"user": ref("User"), "revoked_tokens": {"type": "integer", "example": 2}}})},
            }
        },
        "/api/admin/rooms": {
            "get": {
                "tags": ["Администрирование"],
                "summary": "Список комнат для админа",
                "security": bearer(),
                "parameters": [
                    {"name": "status", "in": "query", "required": False, "schema": {"type": "string", "enum": ["waiting", "playing", "finished", "closed"]}},
                    limit_param(50, 200),
                    offset_param(),
                ],
                "responses": {"200": success({"type": "array", "items": ref("Room")}), "403": error_response("Admin access required", "admin_required")},
            }
        },
        "/api/admin/rooms/{room_id}": {
            "delete": {
                "tags": ["Администрирование"],
                "summary": "Удалить комнату",
                "description": "Удаляет комнату, связанную игру, ходы и чат. После удаления по старым ссылкам нельзя войти в комнату или сделать ход.",
                "security": bearer(),
                "parameters": [path_param("room_id", "ID комнаты")],
                "responses": {"200": success({"type": "object", "properties": {"deleted": {"type": "boolean"}, "room_id": {"type": "integer"}}}), "404": error_response("Room not found", "not_found")},
            }
        },
        "/api/admin/rooms/{room_id}/status": {
            "patch": {
                "tags": ["Администрирование"],
                "summary": "Изменить статус комнаты",
                "description": "Статус closed закрывает комнату администратором. Если в комнате была активная игра, она завершается и новые ходы блокируются.",
                "security": bearer(),
                "parameters": [path_param("room_id", "ID комнаты")],
                "requestBody": json_body("RoomStatusUpdateRequest", "Новый статус комнаты", {"status": "closed"}),
                "responses": {"200": success(ref("Room")), "404": error_response("Room not found", "not_found")},
            }
        },
        "/api/admin/audit": {
            "get": {
                "tags": ["Администрирование"],
                "summary": "Журнал действий",
                "description": "Требуется пользователь с is_admin=true.",
                "security": bearer(),
                "parameters": [limit_param(100, 500)],
                "responses": {"200": success({"type": "array", "items": ref("AuditLog")}), "403": error_response("Admin access required", "admin_required")},
            }
        },
    }


def websocket_events() -> list[dict[str, Any]]:
    return [
        {"event": "connect", "direction": "client->server", "description": "Подключение к Socket.IO. Сервер отвечает событием connected."},
        {"event": "user.join", "direction": "client->server", "payload": {"token": "Bearer token"}, "description": "Авторизует socket-сессию и подключает к комнате user:{id}."},
        {"event": "room.subscribe", "direction": "client->server", "payload": {"room_id": 1}, "description": "Подписывает клиента на события комнаты room:{id}."},
        {"event": "room.unsubscribe", "direction": "client->server", "payload": {"room_id": 1}, "description": "Отписывает клиента от комнаты."},
        {"event": "room.join", "direction": "client->server", "payload": {"token": "token", "room_id": 1, "symbol": "O", "ready": True}, "description": "Присоединиться к комнате через WebSocket."},
        {"event": "room.ready", "direction": "client->server", "payload": {"token": "token", "room_id": 1, "ready": True}, "description": "Изменить готовность."},
        {"event": "game.move", "direction": "client->server", "payload": {"token": "token", "game_id": 1, "row": 0, "col": 0}, "description": "Сделать ход."},
        {"event": "chat.send", "direction": "client->server", "payload": {"token": "token", "room_id": 1, "body": "Привет!"}, "description": "Отправить сообщение."},
        {"event": "matchmaking.queue", "direction": "client->server", "payload": {"token": "token", "board_size": 3, "win_length": 3}, "description": "Встать в очередь матчмейкинга."},
        {"event": "room.updated", "direction": "server->client", "description": "Рассылается подписчикам комнаты при изменении состояния."},
        {"event": "game.move_made", "direction": "server->client", "description": "Рассылается после принятого хода."},
        {"event": "game.finished", "direction": "server->client", "description": "Рассылается после завершения партии."},
        {"event": "chat.message", "direction": "server->client", "description": "Новое сообщение в комнате."},
        {"event": "matchmaking.matched", "direction": "server->client", "description": "Игроку найден соперник."},
    ]
