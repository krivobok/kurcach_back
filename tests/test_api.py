from __future__ import annotations

from conftest import auth_headers, register


def test_health_endpoint(client):
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.get_json()["data"]["status"] == "ok"


def test_register_login_create_ai_room_and_move(client):
    session = register(client, "api_player")
    token = session["token"]

    login_response = client.post("/api/auth/login", json={"username": "api_player", "password": "secret123"})
    assert login_response.status_code == 200

    room_response = client.post(
        "/api/rooms",
        headers=auth_headers(token),
        json={"name": "API AI room", "mode": "ai", "board_size": 3, "win_length": 3},
    )
    assert room_response.status_code == 201, room_response.get_data(as_text=True)
    room = room_response.get_json()["data"]
    game_id = room["game"]["id"]

    move_response = client.post(
        f"/api/games/{game_id}/moves",
        headers=auth_headers(token),
        json={"row": 0, "col": 0},
    )

    assert move_response.status_code == 201, move_response.get_data(as_text=True)
    payload = move_response.get_json()["data"]
    assert payload["game"]["move_count"] == 2
    assert payload["ai_move"]["symbol"] == "O"


def test_two_players_can_finish_game_via_api(client):
    alice = register(client, "api_alice")
    bob = register(client, "api_bob")

    room_response = client.post(
        "/api/rooms",
        headers=auth_headers(alice["token"]),
        json={"name": "API room", "mode": "public", "symbol": "X"},
    )
    room_id = room_response.get_json()["data"]["id"]

    join_response = client.post(
        f"/api/rooms/{room_id}/join",
        headers=auth_headers(bob["token"]),
        json={"symbol": "O"},
    )
    game_id = join_response.get_json()["data"]["game"]["id"]

    moves = [
        (alice["token"], 0, 0),
        (bob["token"], 1, 0),
        (alice["token"], 0, 1),
        (bob["token"], 1, 1),
        (alice["token"], 0, 2),
    ]
    final = None
    for token, row, col in moves:
        final = client.post(
            f"/api/games/{game_id}/moves",
            headers=auth_headers(token),
            json={"row": row, "col": col},
        )

    assert final is not None
    assert final.status_code == 201, final.get_data(as_text=True)
    assert final.get_json()["data"]["game"]["winner_symbol"] == "X"

    replay = client.get(f"/api/games/{game_id}/replay")
    assert len(replay.get_json()["data"]["states"]) == 6
