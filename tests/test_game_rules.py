from __future__ import annotations

import pytest

from app.services.game_rules import GameRuleError, TicTacToeRules


def test_detects_row_column_and_diagonal_winners():
    board = TicTacToeRules.new_board(3)
    row_win = [["X", "X", "X"], [None, "O", None], [None, None, "O"]]
    col_win = [["O", "X", None], ["O", "X", None], ["O", None, "X"]]
    diagonal_win = [["X", "O", None], [None, "X", "O"], [None, None, "X"]]

    assert TicTacToeRules.detect_winner(row_win, 3).symbol == "X"
    assert TicTacToeRules.detect_winner(col_win, 3).line == [(0, 0), (1, 0), (2, 0)]
    assert TicTacToeRules.detect_winner(diagonal_win, 3).symbol == "X"
    assert TicTacToeRules.detect_winner(board, 3).symbol is None


def test_rejects_invalid_or_occupied_move():
    board = TicTacToeRules.apply_move(TicTacToeRules.new_board(3), 1, 1, "X")

    with pytest.raises(GameRuleError):
        TicTacToeRules.apply_move(board, 1, 1, "O")

    with pytest.raises(GameRuleError):
        TicTacToeRules.apply_move(board, 3, 0, "O")


def test_serialization_round_trip_and_public_board():
    board = TicTacToeRules.new_board(4)
    board = TicTacToeRules.apply_move(board, 2, 2, "O")
    raw = TicTacToeRules.serialize(board)

    assert TicTacToeRules.deserialize(raw, 4) == board
    assert TicTacToeRules.public_board(board)[2][2] == "O"
    assert TicTacToeRules.public_board(board)[0][0] == ""


def test_best_move_wins_before_blocking():
    board = [["X", "X", None], ["O", "O", None], [None, None, None]]
    best = TicTacToeRules.best_move(board, "X", 3)

    assert best is not None
    assert (best.row, best.col) == (0, 2)
    assert best.reason == "minimax"


def test_large_board_winner_by_win_length():
    board = TicTacToeRules.new_board(5)
    for col in range(4):
        board = TicTacToeRules.apply_move(board, 2, col, "O")

    winner = TicTacToeRules.detect_winner(board, 4)

    assert winner.symbol == "O"
    assert winner.line == [(2, 0), (2, 1), (2, 2), (2, 3)]
