from __future__ import annotations

from app.repositories import GameRepository, RoomRepository, StatsRepository, UserRepository
from app.services.game_rules import TicTacToeRules
from app.utils.security import hash_password


def test_user_room_game_repositories_work_together(app):
    with app.app_context():
        users = UserRepository()
        rooms = RoomRepository()
        games = GameRepository()
        stats = StatsRepository()

        alice = users.create("alice", hash_password("secret123"))
        bob = users.create("bob", hash_password("secret123"))
        room = rooms.create("Repository room", alice.id, board_size=3, win_length=3)
        rooms.add_player(room.id, alice.id, "X", True)
        rooms.add_player(room.id, bob.id, "O", True)
        game = games.create(room.id, 3, 3, alice.id, bob.id)
        rooms.set_current_game(room.id, game.id, "playing")

        board = TicTacToeRules.apply_move(TicTacToeRules.new_board(3), 0, 0, "X")
        move = games.add_move(game.id, alice.id, "X", 0, 0, 1, TicTacToeRules.serialize(board))
        stats.add_move(alice.id)

        assert users.get_by_username("alice").id == alice.id
        assert rooms.active_count(room.id) == 2
        assert games.latest_move(game.id).id == move.id
        assert stats.get(alice.id).moves_made == 1


def test_leaderboard_orders_by_rating(app):
    with app.app_context():
        users = UserRepository()
        stats = StatsRepository()
        alice = users.create("alice_ranked", hash_password("secret123"), rating=1000)
        bob = users.create("bob_ranked", hash_password("secret123"), rating=1100)

        rows = stats.leaderboard(5)

        assert rows[0]["user_id"] == bob.id
        assert {row["user_id"] for row in rows} >= {alice.id, bob.id}
