from __future__ import annotations

import json
import math
from dataclasses import dataclass
from typing import Iterable


Symbol = str
Cell = str | None
Board = list[list[Cell]]


@dataclass(frozen=True)
class MoveIntent:
    row: int
    col: int
    symbol: Symbol


@dataclass(frozen=True)
class WinnerResult:
    symbol: Symbol | None
    line: list[tuple[int, int]]

    @property
    def has_winner(self) -> bool:
        return self.symbol is not None


@dataclass(frozen=True)
class MoveScore:
    row: int
    col: int
    score: int
    reason: str


class GameRuleError(ValueError):
    pass


class TicTacToeRules:
    SYMBOLS = {"X", "O"}

    @staticmethod
    def new_board(size: int) -> Board:
        TicTacToeRules.validate_size(size)
        return [[None for _ in range(size)] for _ in range(size)]

    @staticmethod
    def validate_size(size: int) -> None:
        if size < 3 or size > 10:
            raise GameRuleError("Board size must be between 3 and 10")

    @staticmethod
    def validate_win_length(size: int, win_length: int) -> None:
        TicTacToeRules.validate_size(size)
        if win_length < 3 or win_length > size:
            raise GameRuleError("Win length must be between 3 and board size")

    @staticmethod
    def validate_symbol(symbol: str) -> Symbol:
        symbol = symbol.upper()
        if symbol not in TicTacToeRules.SYMBOLS:
            raise GameRuleError("Symbol must be X or O")
        return symbol

    @staticmethod
    def other(symbol: Symbol) -> Symbol:
        symbol = TicTacToeRules.validate_symbol(symbol)
        return "O" if symbol == "X" else "X"

    @staticmethod
    def serialize(board: Board) -> str:
        return json.dumps(board, separators=(",", ":"), ensure_ascii=True)

    @staticmethod
    def deserialize(raw: str | None, size: int) -> Board:
        if not raw:
            return TicTacToeRules.new_board(size)
        data = json.loads(raw)
        if not isinstance(data, list) or len(data) != size:
            raise GameRuleError("Invalid board payload")
        board: Board = []
        for row in data:
            if not isinstance(row, list) or len(row) != size:
                raise GameRuleError("Invalid board row")
            board.append([cell if cell in TicTacToeRules.SYMBOLS else None for cell in row])
        return board

    @staticmethod
    def public_board(board: Board) -> list[list[str]]:
        return [[cell or "" for cell in row] for row in board]

    @staticmethod
    def available_moves(board: Board) -> list[tuple[int, int]]:
        moves = []
        for row_index, row in enumerate(board):
            for col_index, value in enumerate(row):
                if value is None:
                    moves.append((row_index, col_index))
        return moves

    @staticmethod
    def move_count(board: Board) -> int:
        return sum(1 for row in board for cell in row if cell is not None)

    @staticmethod
    def is_full(board: Board) -> bool:
        return all(cell is not None for row in board for cell in row)

    @staticmethod
    def validate_move(board: Board, row: int, col: int, symbol: str) -> MoveIntent:
        symbol = TicTacToeRules.validate_symbol(symbol)
        size = len(board)
        if row < 0 or col < 0 or row >= size or col >= size:
            raise GameRuleError("Move is outside the board")
        if board[row][col] is not None:
            raise GameRuleError("Cell is already occupied")
        return MoveIntent(row=row, col=col, symbol=symbol)

    @staticmethod
    def apply_move(board: Board, row: int, col: int, symbol: str) -> Board:
        intent = TicTacToeRules.validate_move(board, row, col, symbol)
        next_board = [line[:] for line in board]
        next_board[intent.row][intent.col] = intent.symbol
        return next_board

    @staticmethod
    def build_board(size: int, moves: Iterable[object]) -> Board:
        board = TicTacToeRules.new_board(size)
        for move in moves:
            row = int(getattr(move, "row"))
            col = int(getattr(move, "col"))
            symbol = str(getattr(move, "symbol"))
            board = TicTacToeRules.apply_move(board, row, col, symbol)
        return board

    @staticmethod
    def detect_winner(board: Board, win_length: int) -> WinnerResult:
        size = len(board)
        TicTacToeRules.validate_win_length(size, win_length)
        directions = [(0, 1), (1, 0), (1, 1), (1, -1)]
        for row in range(size):
            for col in range(size):
                symbol = board[row][col]
                if symbol is None:
                    continue
                for delta_row, delta_col in directions:
                    line = TicTacToeRules._line_from(board, row, col, delta_row, delta_col, win_length)
                    if len(line) == win_length and all(board[r][c] == symbol for r, c in line):
                        return WinnerResult(symbol=symbol, line=line)
        return WinnerResult(symbol=None, line=[])

    @staticmethod
    def _line_from(board: Board, row: int, col: int, delta_row: int, delta_col: int, length: int) -> list[tuple[int, int]]:
        size = len(board)
        line = []
        for step in range(length):
            r = row + step * delta_row
            c = col + step * delta_col
            if r < 0 or c < 0 or r >= size or c >= size:
                return []
            line.append((r, c))
        return line

    @staticmethod
    def terminal_status(board: Board, win_length: int) -> tuple[str, WinnerResult]:
        winner = TicTacToeRules.detect_winner(board, win_length)
        if winner.has_winner:
            return "win", winner
        if TicTacToeRules.is_full(board):
            return "draw", winner
        return "playing", winner

    @staticmethod
    def replay_states(size: int, moves: Iterable[object]) -> list[dict[str, object]]:
        board = TicTacToeRules.new_board(size)
        states = [{"move_number": 0, "board": TicTacToeRules.public_board(board), "symbol": None}]
        for move in moves:
            board = TicTacToeRules.apply_move(board, int(getattr(move, "row")), int(getattr(move, "col")), str(getattr(move, "symbol")))
            states.append(
                {
                    "move_number": int(getattr(move, "move_number")),
                    "board": TicTacToeRules.public_board(board),
                    "symbol": str(getattr(move, "symbol")),
                    "row": int(getattr(move, "row")),
                    "col": int(getattr(move, "col")),
                }
            )
        return states

    @staticmethod
    def score_available_moves(board: Board, symbol: Symbol, win_length: int) -> list[MoveScore]:
        symbol = TicTacToeRules.validate_symbol(symbol)
        opponent = TicTacToeRules.other(symbol)
        scores = []
        for row, col in TicTacToeRules.available_moves(board):
            next_board = TicTacToeRules.apply_move(board, row, col, symbol)
            winner = TicTacToeRules.detect_winner(next_board, win_length)
            if winner.symbol == symbol:
                scores.append(MoveScore(row, col, 10_000, "winning_move"))
                continue
            block_board = TicTacToeRules.apply_move(board, row, col, opponent)
            opponent_win = TicTacToeRules.detect_winner(block_board, win_length)
            if opponent_win.symbol == opponent:
                scores.append(MoveScore(row, col, 9_000, "blocks_opponent"))
                continue
            score = TicTacToeRules._positional_score(board, row, col, symbol, win_length)
            scores.append(MoveScore(row, col, score, "positional"))
        return sorted(scores, key=lambda item: (-item.score, item.row, item.col))

    @staticmethod
    def best_move(board: Board, symbol: Symbol, win_length: int, difficulty: str = "hard") -> MoveScore | None:
        moves = TicTacToeRules.available_moves(board)
        if not moves:
            return None
        symbol = TicTacToeRules.validate_symbol(symbol)
        if difficulty == "easy":
            row, col = moves[0]
            return MoveScore(row, col, 1, "first_available")
        if len(board) == 3 and win_length == 3 and difficulty == "hard":
            row, col, score = TicTacToeRules._minimax_best(board, symbol)
            return MoveScore(row, col, score, "minimax")
        return TicTacToeRules.score_available_moves(board, symbol, win_length)[0]

    @staticmethod
    def _positional_score(board: Board, row: int, col: int, symbol: Symbol, win_length: int) -> int:
        size = len(board)
        center = (size - 1) / 2
        center_bonus = int(20 - (abs(row - center) + abs(col - center)) * 4)
        line_bonus = 0
        for delta_row, delta_col in [(0, 1), (1, 0), (1, 1), (1, -1)]:
            for offset in range(win_length):
                start_row = row - offset * delta_row
                start_col = col - offset * delta_col
                line = TicTacToeRules._line_from(board, start_row, start_col, delta_row, delta_col, win_length)
                if not line:
                    continue
                values = [board[r][c] for r, c in line]
                if TicTacToeRules.other(symbol) not in values:
                    line_bonus += 2 ** values.count(symbol)
        return center_bonus + line_bonus

    @staticmethod
    def _minimax_best(board: Board, symbol: Symbol) -> tuple[int, int, int]:
        best = (-math.inf, -1, -1)
        for row, col in TicTacToeRules.available_moves(board):
            candidate = TicTacToeRules.apply_move(board, row, col, symbol)
            score = TicTacToeRules._minimax(candidate, TicTacToeRules.other(symbol), symbol, depth=0, alpha=-math.inf, beta=math.inf)
            if score > best[0]:
                best = (score, row, col)
        return best[1], best[2], int(best[0])

    @staticmethod
    def _minimax(board: Board, turn: Symbol, maximizer: Symbol, depth: int, alpha: float, beta: float) -> int:
        status, winner = TicTacToeRules.terminal_status(board, 3)
        if status == "win":
            if winner.symbol == maximizer:
                return 10 - depth
            return depth - 10
        if status == "draw":
            return 0
        if turn == maximizer:
            value = -math.inf
            for row, col in TicTacToeRules.available_moves(board):
                value = max(value, TicTacToeRules._minimax(TicTacToeRules.apply_move(board, row, col, turn), TicTacToeRules.other(turn), maximizer, depth + 1, alpha, beta))
                alpha = max(alpha, value)
                if beta <= alpha:
                    break
            return int(value)
        value = math.inf
        for row, col in TicTacToeRules.available_moves(board):
            value = min(value, TicTacToeRules._minimax(TicTacToeRules.apply_move(board, row, col, turn), TicTacToeRules.other(turn), maximizer, depth + 1, alpha, beta))
            beta = min(beta, value)
            if beta <= alpha:
                break
        return int(value)
