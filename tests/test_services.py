from __future__ import annotations

from app.services.auth_service import AuthService
from app.services.game_service import GameService


def test_full_two_player_game_updates_stats(app):
    with app.app_context():
        auth = AuthService()
        service = GameService()
        alice = auth.register("alice_service", "secret123")["user"]
        bob = auth.register("bob_service", "secret123")["user"]
        alice_user = auth.users.get_by_id(alice["id"])
        bob_user = auth.users.get_by_id(bob["id"])

        room = service.create_room(actor=alice_user, name="Service room")
        room = service.join_room(bob_user, room["id"], symbol="O")
        game_id = room["game"]["id"]

        service.make_move(alice_user, game_id, 0, 0)
        service.make_move(bob_user, game_id, 1, 0)
        service.make_move(alice_user, game_id, 0, 1)
        service.make_move(bob_user, game_id, 1, 1)
        final = service.make_move(alice_user, game_id, 0, 2)

        alice_stats = service.stats.get(alice["id"])
        bob_stats = service.stats.get(bob["id"])

        assert final["game"]["status"] == "finished"
        assert final["game"]["winner_symbol"] == "X"
        assert alice_stats.wins == 1
        assert bob_stats.losses == 1


def test_ai_room_auto_replies_to_player_move(app):
    with app.app_context():
        auth = AuthService()
        service = GameService()
        session = auth.register("ai_player", "secret123")
        user = auth.users.get_by_id(session["user"]["id"])
        room = service.create_room(user, "AI room", mode="ai")
        game_id = room["game"]["id"]

        result = service.make_move(user, game_id, 0, 0)

        assert result["game"]["move_count"] == 2
        assert result["ai_move"]["symbol"] == "O"
