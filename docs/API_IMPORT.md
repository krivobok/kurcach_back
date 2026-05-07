# API: Swagger, OpenAPI и Postman

Документ описывает, как проверить REST API проекта через Swagger UI и Postman.

## Swagger UI

1. Запустите сервер:

```powershell
python run.py
```

2. Откройте:

```text
http://127.0.0.1:5000/swagger
```

3. Выполните `/api/auth/register` или `/api/auth/login`.
4. Скопируйте `data.token`.
5. Нажмите `Authorize`.
6. Вставьте токен.

После этого защищённые endpoints можно запускать прямо из Swagger.

## OpenAPI JSON

Машинная спецификация:

```text
http://127.0.0.1:5000/api/openapi.json
```

Локальный файл:

```text
docs/openapi.json
```

Спецификация содержит:

- описания REST endpoints;
- параметры пути и query-параметры;
- схемы запросов и ответов;
- схемы ошибок;
- Bearer Token авторизацию;
- ручки анализа позиции, истории партий и каталога достижений;
- админские endpoints;
- список WebSocket-событий в поле `x-websocket-events`.

## Postman collection

Импорт по URL:

```text
http://127.0.0.1:5000/api/postman.json
```

Локальный файл:

```text
docs/postman_collection.json
```

## Postman environment

Импорт по URL:

```text
http://127.0.0.1:5000/api/postman-environment.json
```

Локальный файл:

```text
docs/postman_environment.json
```

## Переменные Postman

Коллекция использует:

- `base_url` - адрес сервера;
- `token` - Bearer Token;
- `username` - логин тестового пользователя;
- `password` - пароль;
- `admin_code` - код регистрации администратора;
- `user_id` - ID пользователя;
- `room_id` - ID комнаты;
- `game_id` - ID игры.

## Рекомендуемые сценарии

### Обычная игра с компьютером

1. `Auth / Register client`
2. `Rooms / Create AI room`
3. `Games / Make move 0,0`
4. `Games / Game analysis`
5. `Games / Game detail`
6. `Games / Replay`

### Проверка статистики и достижений

1. `Stats / Leaderboard`
2. `Stats / Achievement catalog`
3. `Users / User recent games`

### Админский сценарий

1. `Auth / Register admin`
2. `Admin / Admin dashboard`
3. `Admin / Admin users`
4. `Admin / Admin rooms`
5. `Admin / Close room`
6. `Admin / Delete room`
7. `Admin / Audit log`

Коллекция автоматически сохраняет `token`, `user_id`, `room_id` и `game_id`, поэтому следующие запросы можно запускать без ручного копирования значений.
