from __future__ import annotations

from functools import wraps
from typing import Any, Callable, TypeVar

from flask import Blueprint, g, request

from ..repositories import AuditRepository, ConflictError, NotFoundError, UserRepository
from ..services.admin_service import AdminService, AdminServiceError
from ..services.auth_service import AuthError, AuthService
from ..services.game_service import GameService, GameServiceError
from ..services.statistics_service import StatisticsService
from ..utils.pagination import get_pagination
from ..utils.responses import error, ok
from ..utils.validators import (
    ValidationError,
    bool_value,
    int_range,
    optional_str,
    required_str,
    require_json,
    validate_symbol,
)


api_bp = Blueprint("api", __name__)
F = TypeVar("F", bound=Callable[..., Any])


def bearer_token() -> str | None:
    header = request.headers.get("Authorization", "")
    if header.lower().startswith("bearer "):
        return header.split(" ", 1)[1].strip()
    return request.cookies.get("token")


def login_required(func: F) -> F:
    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any):
        user = AuthService().authenticate_token(bearer_token())
        if user is None:
            return error("Authentication required", 401, "auth_required")
        g.current_user = user
        return func(*args, **kwargs)

    return wrapper  # type: ignore[return-value]


def admin_required(func: F) -> F:
    @wraps(func)
    @login_required
    def wrapper(*args: Any, **kwargs: Any):
        if not g.current_user.is_admin:
            return error("Admin access required", 403, "admin_required")
        return func(*args, **kwargs)

    return wrapper  # type: ignore[return-value]


@api_bp.errorhandler(ValidationError)
def handle_validation(exc: ValidationError):
    return error(str(exc), 422, "validation_error", {"field": exc.field})


@api_bp.errorhandler(AuthError)
def handle_auth(exc: AuthError):
    return error(str(exc), 400, "auth_error")


@api_bp.errorhandler(GameServiceError)
def handle_game(exc: GameServiceError):
    return error(str(exc), exc.status_code, "game_error")


@api_bp.errorhandler(AdminServiceError)
def handle_admin(exc: AdminServiceError):
    return error(str(exc), exc.status_code, "admin_error")


@api_bp.errorhandler(NotFoundError)
def handle_not_found(exc: NotFoundError):
    return error(str(exc), 404, "not_found")


@api_bp.errorhandler(ConflictError)
def handle_conflict(exc: ConflictError):
    return error(str(exc), 409, "conflict")


@api_bp.get("/health")
def health():
    return ok({"service": "tic-tac-toe-backend", "status": "ok"})


@api_bp.post("/auth/register")
def register():
    payload = require_json(request.get_json(silent=True))
    data = AuthService().register(
        username=required_str(payload, "username", 3, 32),
        password=required_str(payload, "password", 6, 128),
        display_name=optional_str(payload, "display_name", 80),
        email=optional_str(payload, "email", 120),
        avatar_url=optional_str(payload, "avatar_url", 500),
        account_type=payload.get("account_type", "client"),
        admin_code=optional_str(payload, "admin_code", 120),
    )
    return ok(data, "Registered", 201)


@api_bp.post("/auth/login")
def login():
    payload = require_json(request.get_json(silent=True))
    data = AuthService().login(
        username=required_str(payload, "username", 3, 32),
        password=required_str(payload, "password", 1, 128),
    )
    return ok(data, "Logged in")


@api_bp.post("/auth/logout")
@login_required
def logout():
    revoked = AuthService().logout(bearer_token(), g.current_user.id)
    return ok({"revoked": revoked})


@api_bp.get("/auth/me")
@login_required
def me():
    return ok(g.current_user.public())


@api_bp.patch("/auth/me")
@login_required
def update_me():
    payload = require_json(request.get_json(silent=True))
    profile = AuthService().update_profile(
        g.current_user.id,
        optional_str(payload, "display_name", 80),
        optional_str(payload, "email", 120),
        optional_str(payload, "avatar_url", 500),
    )
    return ok(profile)


@api_bp.get("/users")
@login_required
def users():
    query = request.args.get("q", "").strip()
    limit, offset = get_pagination(20, 100)
    repo = UserRepository()
    if query:
        items = repo.search(query, limit)
    else:
        items = repo.list(limit, offset)
    return ok([user.public() for user in items])


@api_bp.get("/users/<int:user_id>")
@login_required
def user_detail(user_id: int):
    return ok(StatisticsService().user_dashboard(user_id))


@api_bp.get("/users/<int:user_id>/games")
@login_required
def user_games(user_id: int):
    limit, _ = get_pagination(10, 50)
    return ok(StatisticsService().recent_games(user_id, limit))


@api_bp.get("/rooms")
def list_rooms():
    limit, offset = get_pagination(30, 100)
    status = request.args.get("status")
    return ok(GameService().list_rooms(status=status, limit=limit, offset=offset))


@api_bp.post("/rooms")
@login_required
def create_room():
    payload = require_json(request.get_json(silent=True))
    board_size = int_range(payload, "board_size", 3, 3, 10)
    win_length = int_range(payload, "win_length", min(3, board_size), 3, board_size)
    data = GameService().create_room(
        actor=g.current_user,
        name=required_str(payload, "name", 1, 80),
        mode=payload.get("mode", "public"),
        board_size=board_size,
        win_length=win_length,
        symbol=validate_symbol(payload.get("symbol", "X")),
        ready=bool_value(payload, "ready", True),
    )
    return ok(data, "Room created", 201)


@api_bp.get("/rooms/<int:room_id>")
def room_detail(room_id: int):
    return ok(GameService().room_state(room_id))


@api_bp.post("/rooms/<int:room_id>/join")
@login_required
def join_room(room_id: int):
    payload = request.get_json(silent=True) or {}
    data = GameService().join_room(
        actor=g.current_user,
        room_id=room_id,
        symbol=validate_symbol(payload["symbol"]) if payload.get("symbol") else None,
        ready=bool_value(payload, "ready", True),
    )
    return ok(data)


@api_bp.post("/rooms/<int:room_id>/leave")
@login_required
def leave_room(room_id: int):
    return ok(GameService().leave_room(g.current_user, room_id))


@api_bp.patch("/rooms/<int:room_id>/ready")
@login_required
def set_ready(room_id: int):
    payload = require_json(request.get_json(silent=True))
    return ok(GameService().set_ready(g.current_user, room_id, bool_value(payload, "ready", True)))


@api_bp.get("/rooms/<int:room_id>/chat")
def chat_history(room_id: int):
    limit, _ = get_pagination(50, 100)
    return ok(GameService().chat_history(room_id, limit))


@api_bp.post("/rooms/<int:room_id>/chat")
@login_required
def add_chat(room_id: int):
    payload = require_json(request.get_json(silent=True))
    return ok(GameService().add_chat_message(g.current_user, room_id, required_str(payload, "body", 1, 500)), status=201)


@api_bp.post("/rooms/<int:room_id>/rematch")
@login_required
def rematch(room_id: int):
    return ok(GameService().rematch(g.current_user, room_id))


@api_bp.get("/games/<int:game_id>")
def game_detail(game_id: int):
    service = GameService()
    game = service.games.get(game_id)
    return ok(service.serialize_game(game, include_board=True))


@api_bp.post("/games/<int:game_id>/moves")
@login_required
def make_move(game_id: int):
    payload = require_json(request.get_json(silent=True))
    data = GameService().make_move(
        actor=g.current_user,
        game_id=game_id,
        row=int_range(payload, "row", 0, 0, 9),
        col=int_range(payload, "col", 0, 0, 9),
    )
    return ok(data, status=201)


@api_bp.post("/games/<int:game_id>/ai-move")
@login_required
def ai_move(game_id: int):
    payload = request.get_json(silent=True) or {}
    difficulty = payload.get("difficulty", "hard")
    if difficulty not in {"easy", "medium", "hard"}:
        raise ValidationError("difficulty must be easy, medium or hard", "difficulty")
    return ok(GameService().make_ai_move(game_id, difficulty), status=201)


@api_bp.get("/games/<int:game_id>/hint")
@login_required
def hint(game_id: int):
    difficulty = request.args.get("difficulty", "hard")
    return ok(GameService().hint(g.current_user, game_id, difficulty))


@api_bp.post("/games/<int:game_id>/surrender")
@login_required
def surrender(game_id: int):
    return ok(GameService().surrender(g.current_user, game_id))


@api_bp.get("/games/<int:game_id>/replay")
def replay(game_id: int):
    return ok(GameService().replay(game_id))


@api_bp.get("/games/<int:game_id>/analysis")
def game_analysis(game_id: int):
    difficulty = request.args.get("difficulty", "hard")
    if difficulty not in {"easy", "medium", "hard"}:
        raise ValidationError("difficulty must be easy, medium or hard", "difficulty")
    user = AuthService().authenticate_token(bearer_token()) if bearer_token() else None
    return ok(GameService().analyze_game(game_id, user, difficulty))


@api_bp.post("/matchmaking")
@login_required
def queue_matchmaking():
    payload = request.get_json(silent=True) or {}
    board_size = int_range(payload, "board_size", 3, 3, 10)
    win_length = int_range(payload, "win_length", min(3, board_size), 3, board_size)
    return ok(GameService().queue_matchmaking(g.current_user, board_size, win_length))


@api_bp.delete("/matchmaking")
@login_required
def cancel_matchmaking():
    return ok(GameService().cancel_matchmaking(g.current_user))


@api_bp.get("/leaderboard")
def leaderboard():
    limit, _ = get_pagination(20, 100)
    return ok(StatisticsService().leaderboard(limit))


@api_bp.get("/stats/me")
@login_required
def my_stats():
    return ok(StatisticsService().user_dashboard(g.current_user.id))


@api_bp.get("/stats/achievements")
def achievements():
    return ok(StatisticsService().achievement_catalog())


@api_bp.get("/stats/summary")
def summary():
    return ok(StatisticsService().global_summary())


@api_bp.get("/admin/audit")
@admin_required
def audit():
    limit, _ = get_pagination(100, 500)
    return ok(AuditRepository().list(limit))


@api_bp.get("/admin/dashboard")
@admin_required
def admin_dashboard():
    return ok(AdminService().dashboard())


@api_bp.get("/admin/users")
@admin_required
def admin_users():
    limit, offset = get_pagination(50, 200)
    query = request.args.get("q")
    return ok(AdminService().list_users(limit=limit, offset=offset, query=query))


@api_bp.get("/admin/users/<int:user_id>")
@admin_required
def admin_user_detail(user_id: int):
    return ok(AdminService().user_detail(user_id))


@api_bp.patch("/admin/users/<int:user_id>/role")
@admin_required
def admin_user_role(user_id: int):
    payload = require_json(request.get_json(silent=True))
    return ok(AdminService().set_role(g.current_user, user_id, bool_value(payload, "is_admin", False)))


@api_bp.patch("/admin/users/<int:user_id>/status")
@admin_required
def admin_user_status(user_id: int):
    payload = require_json(request.get_json(silent=True))
    return ok(AdminService().set_status(g.current_user, user_id, required_str(payload, "status", 3, 20)))


@api_bp.post("/admin/users/<int:user_id>/tokens/revoke")
@admin_required
def admin_revoke_tokens(user_id: int):
    return ok(AdminService().revoke_tokens(g.current_user, user_id))


@api_bp.delete("/admin/users/<int:user_id>")
@admin_required
def admin_delete_user(user_id: int):
    return ok(AdminService().delete_user(g.current_user, user_id))


@api_bp.get("/admin/rooms")
@admin_required
def admin_rooms():
    limit, offset = get_pagination(50, 200)
    status = request.args.get("status")
    return ok(AdminService().list_rooms(limit=limit, offset=offset, status=status))


@api_bp.patch("/admin/rooms/<int:room_id>/status")
@admin_required
def admin_room_status(room_id: int):
    payload = require_json(request.get_json(silent=True))
    return ok(AdminService().set_room_status(g.current_user, room_id, required_str(payload, "status", 3, 20)))


@api_bp.delete("/admin/rooms/<int:room_id>")
@admin_required
def admin_delete_room(room_id: int):
    return ok(AdminService().delete_room(g.current_user, room_id))
