from __future__ import annotations

from conftest import auth_headers, register


def register_admin(client, username: str = "admin_user") -> dict:
    response = client.post(
        "/api/auth/register",
        json={
            "username": username,
            "password": "secret123",
            "display_name": "Admin User",
            "account_type": "admin",
            "admin_code": "admin-test-code",
        },
    )
    assert response.status_code == 201, response.get_data(as_text=True)
    return response.get_json()["data"]


def test_client_and_admin_registration_flow(client):
    client_session = register(client, "role_client")
    assert client_session["user"]["is_admin"] is False

    wrong_admin = client.post(
        "/api/auth/register",
        json={"username": "bad_admin", "password": "secret123", "account_type": "admin", "admin_code": "wrong"},
    )
    assert wrong_admin.status_code == 400

    admin_session = register_admin(client, "role_admin")
    assert admin_session["user"]["is_admin"] is True


def test_admin_endpoints_require_admin_and_manage_user(client):
    client_session = register(client, "managed_client")
    admin_session = register_admin(client, "manager_admin")

    denied = client.get("/api/admin/dashboard", headers=auth_headers(client_session["token"]))
    assert denied.status_code == 403

    dashboard = client.get("/api/admin/dashboard", headers=auth_headers(admin_session["token"]))
    assert dashboard.status_code == 200
    assert dashboard.get_json()["data"]["users_total"] >= 2

    users = client.get("/api/admin/users", headers=auth_headers(admin_session["token"]))
    assert users.status_code == 200
    assert any(row["username"] == "managed_client" for row in users.get_json()["data"])

    promoted = client.patch(
        f"/api/admin/users/{client_session['user']['id']}/role",
        headers=auth_headers(admin_session["token"]),
        json={"is_admin": True},
    )
    assert promoted.status_code == 200
    assert promoted.get_json()["data"]["is_admin"] is True

    banned = client.patch(
        f"/api/admin/users/{client_session['user']['id']}/status",
        headers=auth_headers(admin_session["token"]),
        json={"status": "banned"},
    )
    assert banned.status_code == 200
    assert banned.get_json()["data"]["status"] == "banned"

    denied_after_ban = client.get("/api/auth/me", headers=auth_headers(client_session["token"]))
    assert denied_after_ban.status_code == 401

    login_banned = client.post("/api/auth/login", json={"username": "managed_client", "password": "secret123"})
    assert login_banned.status_code == 400


def test_admin_can_revoke_delete_and_manage_rooms(client):
    victim = register(client, "delete_me")
    admin = register_admin(client, "room_admin")

    room_response = client.post(
        "/api/rooms",
        headers=auth_headers(admin["token"]),
        json={"name": "Admin room", "mode": "public"},
    )
    room_id = room_response.get_json()["data"]["id"]

    room_status = client.patch(
        f"/api/admin/rooms/{room_id}/status",
        headers=auth_headers(admin["token"]),
        json={"status": "finished"},
    )
    assert room_status.status_code == 200
    assert room_status.get_json()["data"]["status"] == "finished"

    revoked = client.post(
        f"/api/admin/users/{victim['user']['id']}/tokens/revoke",
        headers=auth_headers(admin["token"]),
    )
    assert revoked.status_code == 200
    assert revoked.get_json()["data"]["revoked_tokens"] >= 1

    deleted = client.delete(
        f"/api/admin/users/{victim['user']['id']}",
        headers=auth_headers(admin["token"]),
    )
    assert deleted.status_code == 200
    assert deleted.get_json()["data"]["deleted"] is True


def test_admin_closed_active_room_blocks_moves_and_rematch(client):
    player = register(client, "closed_room_player")
    admin = register_admin(client, "closer_admin")
    room = client.post(
        "/api/rooms",
        headers=auth_headers(player["token"]),
        json={"name": "Room to close", "mode": "ai"},
    ).get_json()["data"]
    game_id = room["game"]["id"]

    closed = client.patch(
        f"/api/admin/rooms/{room['id']}/status",
        headers=auth_headers(admin["token"]),
        json={"status": "closed"},
    )
    assert closed.status_code == 200
    assert closed.get_json()["data"]["status"] == "closed"

    move = client.post(
        f"/api/games/{game_id}/moves",
        headers=auth_headers(player["token"]),
        json={"row": 0, "col": 0},
    )
    assert move.status_code == 400

    rematch = client.post(f"/api/rooms/{room['id']}/rematch", headers=auth_headers(player["token"]))
    assert rematch.status_code == 400


def test_admin_delete_room_removes_room_and_game(client):
    player = register(client, "deleted_room_player")
    admin = register_admin(client, "deleter_admin")
    room = client.post(
        "/api/rooms",
        headers=auth_headers(player["token"]),
        json={"name": "Room to delete", "mode": "ai"},
    ).get_json()["data"]
    game_id = room["game"]["id"]

    deleted = client.delete(
        f"/api/admin/rooms/{room['id']}",
        headers=auth_headers(admin["token"]),
    )
    assert deleted.status_code == 200
    assert deleted.get_json()["data"]["deleted"] is True

    assert client.get(f"/api/rooms/{room['id']}").status_code == 404
    assert client.get(f"/api/games/{game_id}").status_code == 404
    move = client.post(
        f"/api/games/{game_id}/moves",
        headers=auth_headers(player["token"]),
        json={"row": 0, "col": 0},
    )
    assert move.status_code == 404


def test_admin_forced_playing_room_without_game_cannot_be_joined(client):
    owner = register(client, "owner_without_game")
    second = register(client, "second_without_game")
    admin = register_admin(client, "playing_admin")
    room = client.post(
        "/api/rooms",
        headers=auth_headers(owner["token"]),
        json={"name": "Broken status room", "mode": "public"},
    ).get_json()["data"]

    forced = client.patch(
        f"/api/admin/rooms/{room['id']}/status",
        headers=auth_headers(admin["token"]),
        json={"status": "playing"},
    )
    assert forced.status_code == 200

    join = client.post(f"/api/rooms/{room['id']}/join", headers=auth_headers(second["token"]), json={"ready": True})
    assert join.status_code == 400


def test_admin_page_and_assets(client):
    page = client.get("/admin")
    html = page.get_data(as_text=True)

    assert page.status_code == 200
    assert "Админ-панель" in html
    assert "Создать администратора" in html
    assert "/web/register" in html
