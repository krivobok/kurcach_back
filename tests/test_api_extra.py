from __future__ import annotations

from conftest import auth_headers, register


def test_profile_user_search_pages_and_stats(client):
    session = register(client, "profile_user")
    headers = auth_headers(session["token"])

    me = client.get("/api/auth/me", headers=headers)
    assert me.status_code == 200
    assert me.get_json()["data"]["username"] == "profile_user"

    patch = client.patch(
        "/api/auth/me",
        headers=headers,
        json={"display_name": "Profile Hero", "email": "profile@example.com"},
    )
    assert patch.status_code == 200
    assert patch.get_json()["data"]["display_name"] == "Profile Hero"

    users = client.get("/api/users?q=profile", headers=headers)
    assert users.status_code == 200
    assert users.get_json()["data"][0]["username"] == "profile_user"

    user_id = session["user"]["id"]
    detail = client.get(f"/api/users/{user_id}", headers=headers)
    assert detail.status_code == 200
    assert detail.get_json()["data"]["stats"]["games_played"] == 0

    assert client.get("/").status_code == 200
    assert client.get("/demo").status_code == 200
    assert client.get("/leaderboard").status_code == 200
    assert client.get("/api/stats/me", headers=headers).status_code == 200
    assert client.get("/api/stats/achievements").status_code == 200
    assert client.get("/api/stats/summary").status_code == 200


def test_validation_and_auth_errors(client):
    assert client.get("/api/auth/me").status_code == 401

    invalid = client.post("/api/auth/register", json={"username": "no", "password": "123"})
    assert invalid.status_code == 422

    login = client.post("/api/auth/login", json={"username": "missing", "password": "secret123"})
    assert login.status_code == 400


def test_chat_hint_surrender_and_rematch(client):
    alice = register(client, "chat_alice")
    bob = register(client, "chat_bob")

    room = client.post(
        "/api/rooms",
        headers=auth_headers(alice["token"]),
        json={"name": "Chat room", "mode": "public", "symbol": "X"},
    ).get_json()["data"]
    room_id = room["id"]

    joined = client.post(
        f"/api/rooms/{room_id}/join",
        headers=auth_headers(bob["token"]),
        json={"symbol": "O"},
    ).get_json()["data"]
    game_id = joined["game"]["id"]

    chat = client.post(
        f"/api/rooms/{room_id}/chat",
        headers=auth_headers(alice["token"]),
        json={"body": "hello"},
    )
    assert chat.status_code == 201
    assert client.get(f"/api/rooms/{room_id}/chat").get_json()["data"][0]["body"] == "hello"

    hint = client.get(f"/api/games/{game_id}/hint", headers=auth_headers(alice["token"]))
    assert hint.status_code == 200
    assert hint.get_json()["data"]["best"] is not None

    surrender = client.post(f"/api/games/{game_id}/surrender", headers=auth_headers(bob["token"]))
    assert surrender.status_code == 200
    assert surrender.get_json()["data"]["winner_symbol"] == "X"

    rematch = client.post(f"/api/rooms/{room_id}/rematch", headers=auth_headers(alice["token"]))
    assert rematch.status_code == 200
    assert rematch.get_json()["data"]["game"]["status"] == "playing"


def test_game_analysis_achievements_catalog_and_recent_games(client):
    alice = register(client, "analysis_alice")
    bob = register(client, "analysis_bob")

    room = client.post(
        "/api/rooms",
        headers=auth_headers(alice["token"]),
        json={"name": "Analysis room", "mode": "public", "symbol": "X"},
    ).get_json()["data"]
    joined = client.post(
        f"/api/rooms/{room['id']}/join",
        headers=auth_headers(bob["token"]),
        json={"symbol": "O"},
    ).get_json()["data"]
    game_id = joined["game"]["id"]

    assert client.post(f"/api/games/{game_id}/moves", headers=auth_headers(alice["token"]), json={"row": 0, "col": 0}).status_code == 201
    assert client.post(f"/api/games/{game_id}/moves", headers=auth_headers(bob["token"]), json={"row": 1, "col": 0}).status_code == 201
    assert client.post(f"/api/games/{game_id}/moves", headers=auth_headers(alice["token"]), json={"row": 0, "col": 1}).status_code == 201

    analysis = client.get(f"/api/games/{game_id}/analysis")
    assert analysis.status_code == 200
    data = analysis.get_json()["data"]
    assert data["risk_level"] == "danger"
    assert data["immediate_threats"][0]["row"] == 0
    assert data["immediate_threats"][0]["col"] == 2
    assert data["line_potential"]["X"]["one_move_to_win"] >= 1

    games = client.get(f"/api/users/{alice['user']['id']}/games?limit=5", headers=auth_headers(alice["token"]))
    assert games.status_code == 200
    assert games.get_json()["data"][0]["result_for_user"] == "in_progress"

    achievements = client.get("/api/stats/achievements")
    assert achievements.status_code == 200
    assert any(row["title"] == "Первая победа" for row in achievements.get_json()["data"])


def test_matchmaking_pairs_two_players(client):
    alice = register(client, "match_alice")
    bob = register(client, "match_bob")

    first = client.post("/api/matchmaking", headers=auth_headers(alice["token"]), json={"board_size": 3, "win_length": 3})
    assert first.status_code == 200
    assert first.get_json()["data"]["matched"] is False

    second = client.post("/api/matchmaking", headers=auth_headers(bob["token"]), json={"board_size": 3, "win_length": 3})
    assert second.status_code == 200
    data = second.get_json()["data"]
    assert data["matched"] is True
    assert data["room"]["game"]["status"] == "playing"

    cancel = client.delete("/api/matchmaking", headers=auth_headers(alice["token"]))
    assert cancel.status_code == 200
