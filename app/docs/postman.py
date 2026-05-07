from __future__ import annotations

from typing import Any


SCHEMA_URL = "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"


def build_postman_collection() -> dict[str, Any]:
    return {
        "info": {
            "_postman_id": "7d5f90f0-ttt-course-project",
            "name": "Крестики-нолики: серверные запросы",
            "description": (
                "Подробная коллекция запросов для серверной части проекта «Крестики-нолики». "
                "Коллекция покрывает регистрацию, авторизацию, комнаты, игру, чат, повтор партии, "
                "матчмейкинг, статистику, документацию запросов и административный аудит. "
                "Начните с раздела авторизации: регистрация или вход: тесты коллекции автоматически "
                "сохранят токен, user_id, room_id и game_id."
            ),
            "schema": SCHEMA_URL,
        },
        "variable": [
            {"key": "base_url", "value": "http://127.0.0.1:5000", "type": "string"},
            {"key": "token", "value": "", "type": "string"},
            {"key": "username", "value": "player_one", "type": "string"},
            {"key": "password", "value": "secret123", "type": "string"},
            {"key": "admin_code", "value": "admin123", "type": "string"},
            {"key": "user_id", "value": "1", "type": "string"},
            {"key": "room_id", "value": "1", "type": "string"},
            {"key": "game_id", "value": "1", "type": "string"},
        ],
        "auth": bearer_auth(),
        "event": [collection_test_script()],
        "item": [
            folder("Система и документация", system_items()),
            folder("Авторизация", auth_items()),
            folder("Пользователи", user_items()),
            folder("Комнаты", room_items()),
            folder("Чат", chat_items()),
            folder("Игры", game_items()),
            folder("Подбор соперника", matchmaking_items()),
            folder("Статистика", stats_items()),
            folder("Администрирование", admin_items()),
            folder("Типовые сценарии", scenario_items()),
        ],
    }


def build_postman_environment() -> dict[str, Any]:
    return {
        "name": "Крестики-нолики Local",
        "values": [
            {"key": "base_url", "value": "http://127.0.0.1:5000", "type": "default", "enabled": True},
            {"key": "token", "value": "", "type": "secret", "enabled": True},
            {"key": "username", "value": "player_one", "type": "default", "enabled": True},
            {"key": "password", "value": "secret123", "type": "secret", "enabled": True},
            {"key": "admin_code", "value": "admin123", "type": "secret", "enabled": True},
            {"key": "user_id", "value": "1", "type": "default", "enabled": True},
            {"key": "room_id", "value": "1", "type": "default", "enabled": True},
            {"key": "game_id", "value": "1", "type": "default", "enabled": True},
        ],
        "_postman_variable_scope": "environment",
    }


def bearer_auth() -> dict[str, Any]:
    return {"type": "bearer", "bearer": [{"key": "token", "value": "{{token}}", "type": "string"}]}


def no_auth() -> dict[str, str]:
    return {"type": "noauth"}


def folder(name: str, items: list[dict[str, Any]]) -> dict[str, Any]:
    return {"name": name, "item": items}


def request_item(
    name: str,
    method: str,
    path: str,
    description: str,
    body: dict[str, Any] | None = None,
    auth: bool = True,
    tests: list[str] | None = None,
    query: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    url: dict[str, Any] = {"raw": f"{{{{base_url}}}}{path}"}
    if query:
        url["query"] = query
    item: dict[str, Any] = {
        "name": name,
        "request": {
            "auth": bearer_auth() if auth else no_auth(),
            "method": method,
            "header": [{"key": "Content-Type", "value": "application/json", "type": "text"}],
            "url": url,
            "description": description,
        },
        "response": [],
    }
    if body is not None:
        item["request"]["body"] = {"mode": "raw", "raw": to_json(body), "options": {"raw": {"language": "json"}}}
    if tests:
        item["event"] = [{"listen": "test", "script": {"type": "text/javascript", "exec": tests}}]
    return item


def to_json(data: dict[str, Any]) -> str:
    import json

    return json.dumps(data, ensure_ascii=False, indent=2)


def collection_test_script() -> dict[str, Any]:
    return {
        "listen": "test",
        "script": {
            "type": "text/javascript",
            "exec": [
                "pm.test('Ответ сервера не содержит ошибку 5xx', function () {",
                "    pm.expect(pm.response.code).to.be.below(500);",
                "});",
                "if (pm.response.headers.get('Content-Type') && pm.response.headers.get('Content-Type').includes('application/json')) {",
                "    const json = pm.response.json();",
                "    if (json && json.ok === false) { console.warn('API error:', json.error); }",
                "}",
            ],
        },
    }


def save_auth_tests() -> list[str]:
    return [
        "pm.test('Ответ авторизации успешен', function () { pm.expect(pm.response.code).to.be.oneOf([200, 201]); });",
        "const json = pm.response.json();",
        "pm.expect(json.ok).to.eql(true);",
        "if (json.data && json.data.token) {",
        "    pm.collectionVariables.set('token', json.data.token);",
        "    pm.environment.set('token', json.data.token);",
        "}",
        "if (json.data && json.data.user) {",
        "    pm.collectionVariables.set('user_id', String(json.data.user.id));",
        "    pm.environment.set('user_id', String(json.data.user.id));",
        "}",
    ]


def save_room_tests() -> list[str]:
    return [
        "pm.test('Ответ комнаты успешен', function () { pm.expect(pm.response.code).to.be.oneOf([200, 201]); });",
        "const json = pm.response.json();",
        "pm.expect(json.ok).to.eql(true);",
        "if (json.data && json.data.id) {",
        "    pm.collectionVariables.set('room_id', String(json.data.id));",
        "    pm.environment.set('room_id', String(json.data.id));",
        "}",
        "if (json.data && json.data.game && json.data.game.id) {",
        "    pm.collectionVariables.set('game_id', String(json.data.game.id));",
        "    pm.environment.set('game_id', String(json.data.game.id));",
        "}",
    ]


def save_game_tests() -> list[str]:
    return [
        "pm.test('Ответ игры успешен', function () { pm.expect(pm.response.code).to.be.oneOf([200, 201]); });",
        "const json = pm.response.json();",
        "pm.expect(json.ok).to.eql(true);",
        "const game = json.data && (json.data.game || json.data);",
        "if (game && game.id) {",
        "    pm.collectionVariables.set('game_id', String(game.id));",
        "    pm.environment.set('game_id', String(game.id));",
        "}",
    ]


def system_items() -> list[dict[str, Any]]:
    return [
        request_item("Проверка сервера", "GET", "/api/health", "Проверяет, что сервер запущен.", auth=False),
        request_item("Файл спецификации", "GET", "/api/openapi.json", "Спецификация серверных запросов.", auth=False),
        request_item("Коллекция запросов", "GET", "/api/postman.json", "Коллекция запросов, которую можно импортировать по URL.", auth=False),
        request_item("Окружение запросов", "GET", "/api/postman-environment.json", "Окружение с адресом сервера и переменными.", auth=False),
    ]


def auth_items() -> list[dict[str, Any]]:
    return [
        request_item(
            "Регистрация клиента",
            "POST",
            "/api/auth/register",
            "Создает пользователя и автоматически сохраняет токен и идентификатор пользователя в переменные запросов.",
            {"username": "{{username}}", "password": "{{password}}", "display_name": "Игрок", "email": "player@example.com", "account_type": "client"},
            auth=False,
            tests=save_auth_tests(),
        ),
        request_item(
            "Регистрация администратора",
            "POST",
            "/api/auth/register",
            "Создает администратора. Нужен код администратора из переменных окружения сервера.",
            {"username": "admin_postman", "password": "{{password}}", "display_name": "Администратор", "account_type": "admin", "admin_code": "{{admin_code}}"},
            auth=False,
            tests=save_auth_tests(),
        ),
        request_item(
            "Вход",
            "POST",
            "/api/auth/login",
            "Входит в существующий аккаунт и сохраняет токен и идентификатор пользователя.",
            {"username": "{{username}}", "password": "{{password}}"},
            auth=False,
            tests=save_auth_tests(),
        ),
        request_item("Текущий пользователь", "GET", "/api/auth/me", "Возвращает текущий профиль по токен доступа."),
        request_item(
            "Update profile",
            "PATCH",
            "/api/auth/me",
            "Обновляет публичные поля профиля.",
            {"display_name": "Игрок из запросов", "email": "updated@example.com", "avatar_url": "https://example.com/avatar.png"},
        ),
        request_item("Выход", "POST", "/api/auth/logout", "Отзывает текущий токен. После этого нужно снова выполнить вход."),
    ]


def user_items() -> list[dict[str, Any]]:
    return [
        request_item("Список пользователей", "GET", "/api/users?limit=20&offset=0", "Список пользователей с пагинацией."),
        request_item("Поиск пользователей", "GET", "/api/users?q=player&limit=10", "Поиск пользователей по логину, имени или email."),
        request_item("Карточка пользователя", "GET", "/api/users/{{user_id}}", "Профиль, статистика и достижения выбранного пользователя."),
        request_item("История партий пользователя", "GET", "/api/users/{{user_id}}/games?limit=10", "История партий пользователя с результатом относительно выбранного игрока."),
    ]


def room_items() -> list[dict[str, Any]]:
    return [
        request_item("Список комнат", "GET", "/api/rooms?limit=30&offset=0", "Список комнат. Можно добавить фильтр по статусу комнаты.", auth=False),
        request_item(
            "Создать игру с компьютером",
            "POST",
            "/api/rooms",
            "Создает комнату против компьютера и сразу стартует игру. Сохраняет идентификаторы комнаты и игры.",
            {"name": "запросов room", "mode": "ai", "board_size": 3, "win_length": 3, "symbol": "X", "ready": True},
            tests=save_room_tests(),
        ),
        request_item(
            "Создать комнату для двух игроков",
            "POST",
            "/api/rooms",
            "Создает комнату для двух игроков. Второй пользователь должен выполнить Join room.",
            {"name": "запросов public room", "mode": "public", "board_size": 3, "win_length": 3, "symbol": "X", "ready": True},
            tests=save_room_tests(),
        ),
        request_item("Состояние комнаты", "GET", "/api/rooms/{{room_id}}", "Состояние комнаты, список игроков и текущая игра.", auth=False),
        request_item("Войти в комнату", "POST", "/api/rooms/{{room_id}}/join", "Присоединиться к комнате вторым игроком.", {"symbol": "O", "ready": True}, tests=save_room_tests()),
        request_item("Покинуть комнату", "POST", "/api/rooms/{{room_id}}/leave", "Покинуть комнату. Если игра активна, это считается сдачей."),
        request_item("Изменить готовность", "PATCH", "/api/rooms/{{room_id}}/ready", "Изменить готовность игрока.", {"ready": True}, tests=save_room_tests()),
        request_item("Реванш", "POST", "/api/rooms/{{room_id}}/rematch", "Начать новую партию в той же комнате.", tests=save_room_tests()),
    ]


def chat_items() -> list[dict[str, Any]]:
    return [
        request_item("История чата", "GET", "/api/rooms/{{room_id}}/chat?limit=50", "Последние сообщения комнаты.", auth=False),
        request_item("Отправить сообщение", "POST", "/api/rooms/{{room_id}}/chat", "Отправляет сообщение от текущего игрока комнаты.", {"body": "Привет, хорошей игры!"}),
    ]


def game_items() -> list[dict[str, Any]]:
    return [
        request_item("Состояние игры", "GET", "/api/games/{{game_id}}", "Состояние игры, поле и доступные ходы.", auth=False, tests=save_game_tests()),
        request_item("Ход 0,0", "POST", "/api/games/{{game_id}}/moves", "Сделать ход в левый верхний угол. В комнате с компьютером сервер сразу ответит ходом компьютера.", {"row": 0, "col": 0}, tests=save_game_tests()),
        request_item("Ход 0,1", "POST", "/api/games/{{game_id}}/moves", "Второй пример хода.", {"row": 0, "col": 1}, tests=save_game_tests()),
        request_item("Ход компьютера", "POST", "/api/games/{{game_id}}/ai-move", "Принудительный ход компьютера за текущий знак.", {"difficulty": "hard"}, tests=save_game_tests()),
        request_item("Подсказка", "GET", "/api/games/{{game_id}}/hint?difficulty=hard", "Подсказка лучшего хода для текущего игрока."),
        request_item("Анализ позиции", "GET", "/api/games/{{game_id}}/analysis?difficulty=hard", "Серверный анализ позиции: лучший ход, угрозы, потенциал линий и рекомендация.", auth=False),
        request_item("Сдаться", "POST", "/api/games/{{game_id}}/surrender", "Сдаться в текущей партии.", tests=save_game_tests()),
        request_item("Повтор партии", "GET", "/api/games/{{game_id}}/повтор партии", "Все состояния поля после каждого хода и события игры.", auth=False),
    ]


def matchmaking_items() -> list[dict[str, Any]]:
    return [
        request_item("Встать в очередь подбора", "POST", "/api/matchmaking", "Поставить пользователя в очередь автоматического подбора.", {"board_size": 3, "win_length": 3}),
        request_item("Отменить подбор", "DELETE", "/api/matchmaking", "Отменить активную очередь матчмейкинга."),
    ]


def stats_items() -> list[dict[str, Any]]:
    return [
        request_item("Рейтинг игроков", "GET", "/api/leaderboard?limit=20", "Рейтинг игроков.", auth=False),
        request_item("Моя статистика", "GET", "/api/stats/me", "Профиль, статистика и достижения текущего пользователя."),
        request_item("Каталог достижений", "GET", "/api/stats/achievements", "Каталог всех достижений и количество получивших.", auth=False),
        request_item("Общая сводка", "GET", "/api/stats/summary", "Общая статистика комнат и игр.", auth=False),
    ]


def admin_items() -> list[dict[str, Any]]:
    return [
        request_item("Сводка администратора", "GET", "/api/admin/dashboard", "Сводка: пользователи, комнаты, игры, последние действия."),
        request_item("Пользователи для администратора", "GET", "/api/admin/users?limit=100", "Список пользователей, роли, статусы и краткая статистика."),
        request_item("Карточка пользователя для администратора", "GET", "/api/admin/users/{{user_id}}", "Подробная карточка пользователя."),
        request_item("Выдать права администратора", "PATCH", "/api/admin/users/{{user_id}}/role", "Выдать роль администратора.", {"is_admin": True}),
        request_item("Забрать права администратора", "PATCH", "/api/admin/users/{{user_id}}/role", "Забрать роль администратора.", {"is_admin": False}),
        request_item("Заблокировать пользователя", "PATCH", "/api/admin/users/{{user_id}}/status", "Заблокировать пользователя и отозвать его токены.", {"status": "banned"}),
        request_item("Разблокировать пользователя", "PATCH", "/api/admin/users/{{user_id}}/status", "Разблокировать пользователя.", {"status": "offline"}),
        request_item("Отозвать токены пользователя", "POST", "/api/admin/users/{{user_id}}/tokens/revoke", "Отозвать все активные токены пользователя."),
        request_item("Удалить пользователя", "DELETE", "/api/admin/users/{{user_id}}", "Удалить пользователя. Нельзя удалить самого себя."),
        request_item("Комнаты для администратора", "GET", "/api/admin/rooms?limit=100", "Админский список комнат, включая закрытые комнаты."),
        request_item("Завершить комнату", "PATCH", "/api/admin/rooms/{{room_id}}/status", "Завершить комнату. Активная игра будет остановлена.", {"status": "finished"}),
        request_item("Закрыть комнату", "PATCH", "/api/admin/rooms/{{room_id}}/status", "Закрыть комнату администратором. Новые входы, ходы и реванши будут заблокированы.", {"status": "closed"}),
        request_item("Удалить комнату", "DELETE", "/api/admin/rooms/{{room_id}}", "Удалить комнату, связанную игру, ходы и чат. Старые ссылки после этого возвращают 404."),
        request_item("Журнал действий", "GET", "/api/admin/audit?limit=100", "Журнал действий. Нужен пользователь с is_admin=true."),
    ]


def scenario_items() -> list[dict[str, Any]]:
    return [
        request_item(
            "1. Регистрация или вход",
            "POST",
            "/api/auth/register",
            "Первый шаг сценария: создать пользователя и сохранить token. Если пользователь уже есть, выполните раздел авторизации: вход.",
            {"username": "{{username}}", "password": "{{password}}", "display_name": "Игрок сценария"},
            auth=False,
            tests=save_auth_tests(),
        ),
        request_item(
            "2. Создать игру с компьютером",
            "POST",
            "/api/rooms",
            "Создать комнату с компьютером, чтобы сразу получить идентификатор игры.",
            {"name": "Сценарий: комната", "mode": "ai", "board_size": 3, "win_length": 3, "symbol": "X", "ready": True},
            tests=save_room_tests(),
        ),
        request_item("3. Первый ход", "POST", "/api/games/{{game_id}}/moves", "Сделать первый ход через запрос.", {"row": 0, "col": 0}, tests=save_game_tests()),
        request_item("4. Текущее состояние игры", "GET", "/api/games/{{game_id}}", "Посмотреть поле после ходов игрока и компьютера.", auth=False, tests=save_game_tests()),
        request_item("5. Повтор партии", "GET", "/api/games/{{game_id}}/повтор партии", "Посмотреть историю партии.", auth=False),
    ]
