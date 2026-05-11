from __future__ import annotations

from flask import Blueprint, flash, redirect, render_template, request, session, url_for

from ..repositories import NotFoundError
from ..services.admin_service import AdminService, AdminServiceError
from ..services.auth_service import AuthError, AuthService
from ..services.game_service import GameService, GameServiceError
from ..services.statistics_service import StatisticsService


pages_bp = Blueprint("pages", __name__)


def current_user():
    token = session.get("token")
    user = AuthService().authenticate_token(token)
    if user is None and token:
        session.pop("token", None)
    return user


def require_user():
    user = current_user()
    if user is None:
        flash("Сначала войдите в аккаунт.", "error")
    return user


def require_admin():
    user = require_user()
    if user is not None and not user.is_admin:
        flash("У аккаунта нет прав администратора.", "error")
        return None
    return user


def back(default: str = "pages.index"):
    return redirect(request.referrer or url_for(default))


def room_anchor(room_id: int):
    return redirect(url_for("pages.room", room_id=room_id, _anchor="game-board"))


@pages_bp.get("/")
def index():
    service = GameService()
    rooms = service.list_rooms(limit=12)
    leaderboard = StatisticsService().leaderboard(10)
    return render_template("index.html", user=current_user(), rooms=rooms, leaderboard=leaderboard)


@pages_bp.post("/web/register")
def web_register():
    try:
        data = AuthService().register(
            username=request.form.get("username", ""),
            password=request.form.get("password", ""),
            display_name=request.form.get("display_name") or request.form.get("username", ""),
            account_type=request.form.get("account_type", "client"),
            admin_code=request.form.get("admin_code") or None,
        )
        session["token"] = data["token"]
        flash("Регистрация выполнена.", "success")
    except (AuthError, ValueError) as exc:
        flash(str(exc), "error")
    return redirect(url_for("pages.index"))


@pages_bp.post("/web/login")
def web_login():
    try:
        data = AuthService().login(request.form.get("username", ""), request.form.get("password", ""))
        session["token"] = data["token"]
        flash("Вход выполнен.", "success")
    except AuthError as exc:
        flash(str(exc), "error")
    return redirect(url_for("pages.index"))


@pages_bp.post("/web/logout")
def web_logout():
    token = session.pop("token", None)
    AuthService().logout(token)
    flash("Вы вышли из аккаунта.", "success")
    return redirect(url_for("pages.index"))


@pages_bp.post("/web/rooms/ai")
def web_create_ai_room():
    user = require_user()
    if user is None:
        return redirect(url_for("pages.index"))
    try:
        room = GameService().create_room(user, f"Игра {user.display_name}", mode="ai")
        flash("Игра с компьютером началась.", "success")
        return redirect(url_for("pages.room", room_id=room["id"]))
    except GameServiceError as exc:
        flash(str(exc), "error")
        return redirect(url_for("pages.index"))


@pages_bp.post("/web/rooms/public")
def web_create_public_room():
    user = require_user()
    if user is None:
        return redirect(url_for("pages.index"))
    name = request.form.get("name") or f"Комната {user.display_name}"
    try:
        room = GameService().create_room(user, name, mode="public")
        flash("Комната создана. Второй игрок может присоединиться из списка.", "success")
        return redirect(url_for("pages.room", room_id=room["id"]))
    except GameServiceError as exc:
        flash(str(exc), "error")
        return redirect(url_for("pages.index"))


@pages_bp.post("/web/rooms/<int:room_id>/join")
def web_join_room(room_id: int):
    user = require_user()
    if user is None:
        return redirect(url_for("pages.index"))
    try:
        GameService().join_room(user, room_id)
        flash("Вы присоединились к комнате.", "success")
        return redirect(url_for("pages.room", room_id=room_id))
    except GameServiceError as exc:
        flash(str(exc), "error")
        return back()


@pages_bp.get("/rooms/<int:room_id>")
def room(room_id: int):
    user = current_user()
    service = GameService()
    try:
        room_state = service.room_state(room_id)
        chat_messages = service.chat_history(room_id)
    except GameServiceError as exc:
        flash(str(exc), "error")
        return redirect(url_for("pages.index"))
    own_symbol = None
    if user:
        for player in room_state.get("players", []):
            if player["user_id"] == user.id:
                own_symbol = player["symbol"]
                break
    analysis = service.analyze_game(room_state["game"]["id"], user) if room_state.get("game") else None
    return render_template("room.html", user=user, room=room_state, own_symbol=own_symbol, analysis=analysis, chat_messages=chat_messages)


@pages_bp.post("/web/games/<int:game_id>/move")
def web_make_move(game_id: int):
    user = require_user()
    if user is None:
        return redirect(url_for("pages.index"))
    try:
        result = GameService().make_move(user, game_id, int(request.form.get("row", 0)), int(request.form.get("col", 0)))
        return room_anchor(result["game"]["room_id"])
    except (GameServiceError, ValueError) as exc:
        flash(str(exc), "error")
    return back()


@pages_bp.post("/web/games/<int:game_id>/hint")
def web_hint(game_id: int):
    user = require_user()
    if user is None:
        return redirect(url_for("pages.index"))
    try:
        hint = GameService().hint(user, game_id)
        best = hint.get("best")
        if best:
            flash(f"Подсказка: строка {best['row'] + 1}, столбец {best['col'] + 1}.", "success")
    except GameServiceError as exc:
        flash(str(exc), "error")
    return back()


@pages_bp.post("/web/games/<int:game_id>/surrender")
def web_surrender(game_id: int):
    user = require_user()
    if user is None:
        return redirect(url_for("pages.index"))
    try:
        GameService().surrender(user, game_id)
        flash("Партия завершена.", "success")
    except GameServiceError as exc:
        flash(str(exc), "error")
    return back()


@pages_bp.post("/web/rooms/<int:room_id>/rematch")
def web_rematch(room_id: int):
    user = require_user()
    if user is None:
        return redirect(url_for("pages.index"))
    try:
        GameService().rematch(user, room_id)
        flash("Реванш начался.", "success")
    except GameServiceError as exc:
        flash(str(exc), "error")
    return redirect(url_for("pages.room", room_id=room_id))


@pages_bp.post("/web/rooms/<int:room_id>/chat")
def web_add_chat(room_id: int):
    user = require_user()
    if user is None:
        return redirect(url_for("pages.index"))
    try:
        GameService().add_chat_message(user, room_id, request.form.get("body", ""))
        flash("Сообщение отправлено.", "success")
    except GameServiceError as exc:
        flash(str(exc), "error")
    return redirect(url_for("pages.room", room_id=room_id, _anchor="room-chat"))


@pages_bp.get("/leaderboard")
def leaderboard():
    return render_template("leaderboard.html", leaderboard=StatisticsService().leaderboard(50))


@pages_bp.get("/demo")
def demo():
    return render_template("demo.html")


@pages_bp.get("/admin")
def admin():
    user = current_user()
    dashboard = users = rooms = audit = None
    if user and user.is_admin:
        admin_service = AdminService()
        dashboard = admin_service.dashboard()
        users = admin_service.list_users(limit=100)
        rooms = admin_service.list_rooms(limit=100)
        audit = admin_service.audit.list(30)
    return render_template("admin.html", user=user, dashboard=dashboard, users=users, rooms=rooms, audit=audit)


@pages_bp.post("/web/admin/users/<int:user_id>/role")
def web_admin_role(user_id: int):
    admin_user = require_admin()
    if admin_user is None:
        return redirect(url_for("pages.admin"))
    try:
        AdminService().set_role(admin_user, user_id, request.form.get("is_admin") == "1")
        flash("Роль пользователя изменена.", "success")
    except AdminServiceError as exc:
        flash(str(exc), "error")
    return redirect(url_for("pages.admin"))


@pages_bp.post("/web/admin/users/<int:user_id>/status")
def web_admin_status(user_id: int):
    admin_user = require_admin()
    if admin_user is None:
        return redirect(url_for("pages.admin"))
    try:
        AdminService().set_status(admin_user, user_id, request.form.get("status", "offline"))
        flash("Статус пользователя изменён.", "success")
    except AdminServiceError as exc:
        flash(str(exc), "error")
    return redirect(url_for("pages.admin"))


@pages_bp.post("/web/admin/users/<int:user_id>/tokens/revoke")
def web_admin_revoke_tokens(user_id: int):
    admin_user = require_admin()
    if admin_user is None:
        return redirect(url_for("pages.admin"))
    try:
        AdminService().revoke_tokens(admin_user, user_id)
        flash("Токены пользователя отозваны.", "success")
    except AdminServiceError as exc:
        flash(str(exc), "error")
    return redirect(url_for("pages.admin"))


@pages_bp.post("/web/admin/users/<int:user_id>/delete")
def web_admin_delete_user(user_id: int):
    admin_user = require_admin()
    if admin_user is None:
        return redirect(url_for("pages.admin"))
    try:
        AdminService().delete_user(admin_user, user_id)
        flash("Пользователь удалён.", "success")
    except AdminServiceError as exc:
        flash(str(exc), "error")
    return redirect(url_for("pages.admin"))


@pages_bp.post("/web/admin/rooms/<int:room_id>/status")
def web_admin_room_status(room_id: int):
    admin_user = require_admin()
    if admin_user is None:
        return redirect(url_for("pages.admin"))
    try:
        AdminService().set_room_status(admin_user, room_id, request.form.get("status", "closed"))
        flash("Статус комнаты изменён.", "success")
    except AdminServiceError as exc:
        flash(str(exc), "error")
    return redirect(url_for("pages.admin"))


@pages_bp.post("/web/admin/rooms/<int:room_id>/delete")
def web_admin_delete_room(room_id: int):
    admin_user = require_admin()
    if admin_user is None:
        return redirect(url_for("pages.admin"))
    try:
        AdminService().delete_room(admin_user, room_id)
        flash("Комната удалена.", "success")
    except AdminServiceError as exc:
        flash(str(exc), "error")
    return redirect(url_for("pages.admin"))
