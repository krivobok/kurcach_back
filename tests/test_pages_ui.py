from __future__ import annotations

import re


def test_main_page_is_russian_clickable_game_screen(client):
    response = client.get("/")
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "Тип аккаунта" in html
    assert "Документация" in html
    assert "/web/register" in html
    assert "/web/login" in html

    response = client.post(
        "/web/register",
        data={"username": "ui_player", "display_name": "Игрок UI", "password": "secret123", "account_type": "client"},
        follow_redirects=True,
    )
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "Играть с компьютером" in html
    assert "Комната для друга" in html
    assert "Профиль" in html
    assert "/web/rooms/ai" in html
    assert "/web/rooms/public" in html


def test_game_static_assets_are_served(client):
    styles = client.get("/static/css/app.css")
    room_script = client.get("/static/js/room.js")

    assert styles.status_code == 200
    css = styles.get_data(as_text=True)
    assert ".server-board" in css
    assert ".server-cell" in css
    assert ".inline-form" in css

    assert room_script.status_code == 200
    script = room_script.get_data(as_text=True)
    assert "data-async-move" in script
    assert "window.scrollTo" in script
    assert "innerHTML" in script


def test_web_move_returns_to_board_without_success_flash(client):
    client.post(
        "/web/register",
        data={"username": "scroll_player", "display_name": "Игрок", "password": "secret123", "account_type": "client"},
        follow_redirects=True,
    )
    created = client.post("/web/rooms/ai", follow_redirects=False)
    room_page = client.get(created.headers["Location"]).get_data(as_text=True)
    game_id = int(re.search(r"/web/games/(\d+)/move", room_page).group(1))

    moved = client.post(f"/web/games/{game_id}/move", data={"row": 0, "col": 0}, follow_redirects=False)

    assert moved.status_code == 302
    assert moved.headers["Location"].endswith("#game-board")
    html = client.get(moved.headers["Location"]).get_data(as_text=True)
    assert "Ход принят" not in html
    assert "data-async-move" in html
    assert "room.js" in html