from __future__ import annotations

import json
from typing import Any

from ..models import Game, Move, Room, User
from ..repositories import (
    AuditRepository,
    ChatRepository,
    ConflictError,
    GameRepository,
    MatchmakingRepository,
    NotFoundError,
    RoomRepository,
    StatsRepository,
)
from ..utils.validators import validate_game_config, validate_symbol
from .game_rules import Board, GameRuleError, TicTacToeRules
from .notifications import NotificationService


class GameServiceError(RuntimeError):
    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.status_code = status_code


class GameService:
    def __init__(self) -> None:
        self.rooms = RoomRepository()
        self.games = GameRepository()
        self.stats = StatsRepository()
        self.chat = ChatRepository()
        self.matchmaking = MatchmakingRepository()
        self.audit = AuditRepository()
        self.notifications = NotificationService()

    def create_room(
        self,
        actor: User,
        name: str,
        mode: str = "public",
        board_size: int = 3,
        win_length: int = 3,
        symbol: str = "X",
        ready: bool = True,
    ) -> dict[str, Any]:
        board_size, win_length = validate_game_config(board_size, win_length)
        if mode not in {"public", "private", "ai", "matchmaking"}:
            raise GameServiceError("Unsupported room mode")
        symbol = validate_symbol(symbol)
        room = self.rooms.create(
            name=name,
            created_by=actor.id,
            mode=mode,
            board_size=board_size,
            win_length=win_length,
            max_players=1 if mode == "ai" else 2,
        )
        try:
            self.rooms.add_player(room.id, actor.id, symbol=symbol, ready=ready)
        except ConflictError as exc:
            raise GameServiceError(str(exc)) from exc
        self.audit.add(actor.id, "create_room", "room", room.id, {"mode": mode})
        if mode == "ai":
            game = self._start_game(room.id)
            self.audit.add(actor.id, "start_ai_game", "game", game.id)
        payload = self.room_state(room.id)
        self.notifications.room_updated(room.id, payload)
        return payload

    def list_rooms(self, status: str | None = None, limit: int = 50, offset: int = 0) -> list[dict[str, Any]]:
        return [
            self.serialize_room(room, include_players=True, include_game=False)
            for room in self.rooms.list(status, limit, offset)
            if room.status != "closed"
        ]

    def room_state(self, room_id: int) -> dict[str, Any]:
        try:
            room = self.rooms.get(room_id)
        except NotFoundError as exc:
            raise GameServiceError("Room not found", 404) from exc
        if room.status == "closed":
            raise GameServiceError("Room is closed", 410)
        return self.serialize_room(room, include_players=True, include_game=True)

    def join_room(self, actor: User, room_id: int, symbol: str | None = None, ready: bool = True) -> dict[str, Any]:
        room = self._room_or_404(room_id)
        if room.status != "waiting" or room.current_game_id is not None:
            raise GameServiceError("Room is not available for joining")
        if room.mode == "ai":
            raise GameServiceError("AI rooms are single-player")
        if self.rooms.active_count(room.id) >= room.max_players:
            raise GameServiceError("Room is full", 409)
        try:
            self.rooms.add_player(room.id, actor.id, symbol=symbol, ready=ready)
        except ConflictError as exc:
            raise GameServiceError(str(exc), 409) from exc
        self.audit.add(actor.id, "join_room", "room", room.id)
        if self.rooms.active_count(room.id) >= room.max_players and room.current_game_id is None:
            self._start_game(room.id)
        payload = self.room_state(room.id)
        self.notifications.room_updated(room.id, payload)
        return payload

    def leave_room(self, actor: User, room_id: int) -> dict[str, Any]:
        room = self._room_or_404(room_id)
        self.rooms.leave(room.id, actor.id)
        self.audit.add(actor.id, "leave_room", "room", room.id)
        if room.current_game_id:
            game = self.games.get(room.current_game_id)
            if game.status == "playing":
                self.surrender(actor, game.id, reason="leave_room")
        if self.rooms.active_count(room.id) == 0:
            self.rooms.update_status(room.id, "finished")
        payload = self.room_state(room.id)
        self.notifications.room_updated(room.id, payload)
        return payload

    def set_ready(self, actor: User, room_id: int, ready: bool) -> dict[str, Any]:
        room = self._room_or_404(room_id)
        if room.status != "waiting":
            raise GameServiceError("Ready state can be changed only in waiting rooms")
        self.rooms.set_ready(room.id, actor.id, ready)
        players = self.rooms.players(room.id)
        if len(players) == room.max_players and all(player["is_ready"] for player in players) and room.current_game_id is None:
            self._start_game(room.id)
        payload = self.room_state(room.id)
        self.notifications.room_updated(room.id, payload)
        return payload

    def make_move(self, actor: User, game_id: int, row: int, col: int) -> dict[str, Any]:
        game = self._game_or_404(game_id)
        self._ensure_game_room_is_playing(game)
        symbol = self._symbol_for_user(game, actor.id)
        payload = self._apply_move(game, actor.id, symbol, row, col, source="player")
        fresh_game = self.games.get(game_id)
        if fresh_game.status == "playing":
            room = self.rooms.get(fresh_game.room_id)
            if room.mode == "ai" and fresh_game.current_turn == "O" and fresh_game.player_o_id is None:
                ai_payload = self.make_ai_move(fresh_game.id, difficulty="hard")
                payload["ai_move"] = ai_payload.get("move")
                payload["game"] = ai_payload["game"]
                payload["board"] = ai_payload["board"]
        return payload

    def make_ai_move(self, game_id: int, difficulty: str = "hard") -> dict[str, Any]:
        game = self._game_or_404(game_id)
        self._ensure_game_room_is_playing(game)
        if game.status != "playing":
            raise GameServiceError("Game is not active")
        board = self.current_board(game.id, game.board_size)
        best = TicTacToeRules.best_move(board, game.current_turn, game.win_length, difficulty=difficulty)
        if best is None:
            raise GameServiceError("No available moves")
        return self._apply_move(game, None, game.current_turn, best.row, best.col, source="ai")

    def hint(self, actor: User, game_id: int, difficulty: str = "hard") -> dict[str, Any]:
        game = self._game_or_404(game_id)
        self._ensure_game_room_is_playing(game)
        symbol = self._symbol_for_user(game, actor.id)
        if game.current_turn != symbol:
            raise GameServiceError("Hint is available only for current player")
        board = self.current_board(game.id, game.board_size)
        scores = TicTacToeRules.score_available_moves(board, symbol, game.win_length)
        best = TicTacToeRules.best_move(board, symbol, game.win_length, difficulty=difficulty)
        return {
            "best": best.__dict__ if best else None,
            "top_moves": [score.__dict__ for score in scores[:5]],
        }

    def surrender(self, actor: User, game_id: int, reason: str = "surrender") -> dict[str, Any]:
        game = self._game_or_404(game_id)
        self._ensure_game_room_is_playing(game)
        if game.status != "playing":
            raise GameServiceError("Game is not active")
        loser_symbol = self._symbol_for_user(game, actor.id)
        winner_symbol = TicTacToeRules.other(loser_symbol)
        winner_user_id = self._user_for_symbol(game, winner_symbol)
        finished = self.games.finish(game.id, winner_symbol, winner_user_id, False, [], game.move_count)
        self.rooms.update_status(game.room_id, "finished")
        self.stats.apply_result(game.player_x_id, game.player_o_id, winner_user_id, False)
        self.games.add_event(game.id, "surrender", {"user_id": actor.id, "reason": reason})
        self.audit.add(actor.id, "surrender", "game", game.id, {"reason": reason})
        payload = self.serialize_game(finished, include_board=True)
        self.notifications.game_finished(game.room_id, payload)
        return payload

    def rematch(self, actor: User, room_id: int) -> dict[str, Any]:
        room = self._room_or_404(room_id)
        if room.status != "finished":
            raise GameServiceError("Rematch is available only after a finished game")
        if room.current_game_id:
            current_game = self.games.get(room.current_game_id)
            if current_game.status != "finished":
                raise GameServiceError("Current game is not finished yet")
        players = self.rooms.players(room.id)
        if not any(player["user_id"] == actor.id for player in players):
            raise GameServiceError("Only room players can request rematch", 403)
        if room.mode != "ai" and len(players) < 2:
            raise GameServiceError("Need two players for rematch")
        game = self._start_game(room.id)
        self.audit.add(actor.id, "rematch", "game", game.id)
        payload = self.room_state(room.id)
        self.notifications.room_updated(room.id, payload)
        return payload

    def replay(self, game_id: int) -> dict[str, Any]:
        game = self._game_or_404(game_id)
        moves = self.games.moves(game.id)
        return {
            "game": game.public(),
            "states": TicTacToeRules.replay_states(game.board_size, moves),
            "events": self.games.events(game.id),
        }

    def analyze_game(self, game_id: int, actor: User | None = None, difficulty: str = "hard") -> dict[str, Any]:
        game = self._game_or_404(game_id)
        board = self.current_board(game.id, game.board_size)
        status, winner = TicTacToeRules.terminal_status(board, game.win_length)
        available = TicTacToeRules.available_moves(board)
        current_symbol = game.current_turn if game.status == "playing" and status == "playing" else winner.symbol or game.current_turn
        opponent = TicTacToeRules.other(current_symbol)
        top_scores = TicTacToeRules.score_available_moves(board, current_symbol, game.win_length) if available and status == "playing" else []
        best = TicTacToeRules.best_move(board, current_symbol, game.win_length, difficulty=difficulty) if available and status == "playing" else None
        winning_moves = {
            "X": self._winning_moves(board, "X", game.win_length),
            "O": self._winning_moves(board, "O", game.win_length),
        }
        current_wins = winning_moves[current_symbol]
        opponent_wins = winning_moves[opponent]
        actor_symbol = self._actor_symbol_or_none(game, actor.id) if actor else None
        return {
            "game": self.serialize_game(game, include_board=True),
            "board_status": status,
            "winner": winner.symbol,
            "current_symbol": current_symbol,
            "opponent_symbol": opponent,
            "actor_symbol": actor_symbol,
            "is_actor_turn": bool(actor_symbol and actor_symbol == game.current_turn and game.status == "playing"),
            "available_moves_count": len(available),
            "filled_cells_count": TicTacToeRules.move_count(board),
            "progress_percent": round(TicTacToeRules.move_count(board) / (game.board_size * game.board_size) * 100, 2),
            "best_move": best.__dict__ if best else None,
            "top_moves": [score.__dict__ for score in top_scores[:7]],
            "winning_moves": winning_moves,
            "immediate_threats": opponent_wins,
            "risk_level": self._analysis_risk(game.status, status, current_wins, opponent_wins),
            "recommendation": self._analysis_recommendation(game.status, status, current_symbol, current_wins, opponent_wins, best),
            "line_potential": {
                "X": self._line_potential(board, "X", game.win_length),
                "O": self._line_potential(board, "O", game.win_length),
            },
            "strategic_zones": self._strategic_zones(board),
        }

    def add_chat_message(self, actor: User, room_id: int, body: str) -> dict[str, Any]:
        room = self._room_or_404(room_id)
        if room.status == "closed":
            raise GameServiceError("Room is closed")
        if not any(player["user_id"] == actor.id for player in self.rooms.players(room.id)):
            raise GameServiceError("Only room players can write to room chat", 403)
        body = body.strip()
        if not body:
            raise GameServiceError("Message cannot be empty")
        if len(body) > 500:
            raise GameServiceError("Message is too long")
        message = self.chat.add(room.id, actor.id, body)
        payload = message.public()
        self.notifications.chat_message(room.id, payload)
        return payload

    def chat_history(self, room_id: int, limit: int = 50) -> list[dict[str, Any]]:
        self._room_or_404(room_id)
        return [message.public() for message in self.chat.list_for_room(room_id, limit)]

    def queue_matchmaking(self, actor: User, board_size: int = 3, win_length: int = 3) -> dict[str, Any]:
        board_size, win_length = validate_game_config(board_size, win_length)
        candidate = self.matchmaking.find_candidate(actor.id, board_size, win_length)
        own_queue = self.matchmaking.queue(actor.id, board_size, win_length)
        if candidate:
            room = self.rooms.create(
                name=f"Match #{candidate['id']}-{own_queue['id']}",
                created_by=actor.id,
                mode="matchmaking",
                board_size=board_size,
                win_length=win_length,
            )
            self.rooms.add_player(room.id, int(candidate["user_id"]), symbol="X", ready=True)
            self.rooms.add_player(room.id, actor.id, symbol="O", ready=True)
            game = self._start_game(room.id)
            self.matchmaking.mark_matched([actor.id, int(candidate["user_id"])], room.id)
            payload = self.serialize_game(game, include_board=True)
            self.notifications.matchmaking_matched(actor.id, payload)
            self.notifications.matchmaking_matched(int(candidate["user_id"]), payload)
            return {"matched": True, "room": self.room_state(room.id)}
        return {"matched": False, "queue": own_queue}

    def cancel_matchmaking(self, actor: User) -> dict[str, Any]:
        return {"cancelled": self.matchmaking.cancel(actor.id)}

    def current_board(self, game_id: int, size: int) -> Board:
        latest = self.games.latest_move(game_id)
        if latest:
            return TicTacToeRules.deserialize(latest.board_after, size)
        return TicTacToeRules.new_board(size)

    def serialize_room(self, room: Room, include_players: bool, include_game: bool) -> dict[str, Any]:
        data = room.public()
        if include_players:
            data["players"] = self.rooms.players(room.id)
        if include_game and room.current_game_id:
            data["game"] = self.serialize_game(self.games.get(room.current_game_id), include_board=True)
        else:
            data["game"] = None
        return data

    def serialize_game(self, game: Game, include_board: bool = False) -> dict[str, Any]:
        data = game.public()
        if game.winning_line:
            try:
                data["winning_line"] = json.loads(game.winning_line)
            except json.JSONDecodeError:
                data["winning_line"] = []
        if include_board:
            board = self.current_board(game.id, game.board_size)
            data["board"] = TicTacToeRules.public_board(board)
            data["available_moves"] = TicTacToeRules.available_moves(board)
        return data

    def _start_game(self, room_id: int) -> Game:
        room = self.rooms.get(room_id)
        if room.status not in {"waiting", "finished"}:
            raise GameServiceError("Room cannot start a new game")
        if room.current_game_id:
            current_game = self.games.get(room.current_game_id)
            if current_game.status == "playing":
                raise GameServiceError("Room already has an active game")
        players = self.rooms.players(room.id)
        player_by_symbol = {player["symbol"]: player["user_id"] for player in players}
        player_x_id = player_by_symbol.get("X")
        player_o_id = player_by_symbol.get("O")
        if room.mode != "ai" and (player_x_id is None or player_o_id is None):
            raise GameServiceError("Need X and O players to start")
        if room.mode == "ai" and player_x_id is None and player_o_id is not None:
            player_x_id, player_o_id = player_o_id, None
        game = self.games.create(room.id, room.board_size, room.win_length, player_x_id, player_o_id)
        self.rooms.set_current_game(room.id, game.id, status="playing")
        self.games.add_event(game.id, "game_started", {"room_id": room.id, "players": players})
        return game

    def _apply_move(self, game: Game, user_id: int | None, symbol: str, row: int, col: int, source: str) -> dict[str, Any]:
        if game.status != "playing":
            raise GameServiceError("Game is not active")
        self._ensure_game_room_is_playing(game)
        symbol = validate_symbol(symbol)
        if symbol != game.current_turn:
            raise GameServiceError("It is not this symbol's turn")
        board = self.current_board(game.id, game.board_size)
        try:
            next_board = TicTacToeRules.apply_move(board, row, col, symbol)
            winner = TicTacToeRules.detect_winner(next_board, game.win_length)
        except GameRuleError as exc:
            raise GameServiceError(str(exc)) from exc
        move_number = game.move_count + 1
        move = self.games.add_move(game.id, user_id, symbol, row, col, move_number, TicTacToeRules.serialize(next_board))
        self.stats.add_move(user_id)
        self.games.add_event(game.id, "move", move.public())
        status, _ = TicTacToeRules.terminal_status(next_board, game.win_length)
        if winner.has_winner:
            winner_user_id = self._user_for_symbol(game, winner.symbol or symbol)
            finished = self.games.finish(game.id, winner.symbol, winner_user_id, False, winner.line, move_number)
            self.rooms.update_status(game.room_id, "finished")
            self.stats.apply_result(game.player_x_id, game.player_o_id, winner_user_id, False)
            unlocked = self._award_achievements(finished)
            payload = self._move_payload(finished, move, next_board, source, unlocked)
            self.notifications.move_made(game.room_id, payload)
            self.notifications.game_finished(game.room_id, payload)
            return payload
        if status == "draw":
            finished = self.games.finish(game.id, None, None, True, [], move_number)
            self.rooms.update_status(game.room_id, "finished")
            self.stats.apply_result(game.player_x_id, game.player_o_id, None, True)
            unlocked = self._award_achievements(finished)
            payload = self._move_payload(finished, move, next_board, source, unlocked)
            self.notifications.move_made(game.room_id, payload)
            self.notifications.game_finished(game.room_id, payload)
            return payload
        updated = self.games.update_turn_and_count(game.id, TicTacToeRules.other(symbol), move_number)
        payload = self._move_payload(updated, move, next_board, source, [])
        self.notifications.move_made(game.room_id, payload)
        return payload

    def _move_payload(self, game: Game, move: Move, board: Board, source: str, unlocked: list[dict[str, Any]]) -> dict[str, Any]:
        return {
            "game": self.serialize_game(game, include_board=False),
            "move": move.public(),
            "board": TicTacToeRules.public_board(board),
            "source": source,
            "achievements": unlocked,
        }

    def _actor_symbol_or_none(self, game: Game, user_id: int) -> str | None:
        if game.player_x_id == user_id:
            return "X"
        if game.player_o_id == user_id:
            return "O"
        return None

    def _winning_moves(self, board: Board, symbol: str, win_length: int) -> list[dict[str, Any]]:
        moves = []
        for row, col in TicTacToeRules.available_moves(board):
            next_board = TicTacToeRules.apply_move(board, row, col, symbol)
            winner = TicTacToeRules.detect_winner(next_board, win_length)
            if winner.symbol == symbol:
                moves.append({"row": row, "col": col, "line": [[r, c] for r, c in winner.line]})
        return moves

    def _line_potential(self, board: Board, symbol: str, win_length: int) -> dict[str, Any]:
        opponent = TicTacToeRules.other(symbol)
        open_lines = 0
        strongest_line = 0
        one_move_to_win = 0
        fork_cells: dict[tuple[int, int], int] = {}
        for line in self._candidate_lines(len(board), win_length):
            values = [board[row][col] for row, col in line]
            if opponent in values:
                continue
            open_lines += 1
            own_count = values.count(symbol)
            empty_count = values.count(None)
            strongest_line = max(strongest_line, own_count)
            if own_count == win_length - 1 and empty_count == 1:
                one_move_to_win += 1
                empty_index = values.index(None)
                fork_cells[line[empty_index]] = fork_cells.get(line[empty_index], 0) + 1
        forks = [
            {"row": row, "col": col, "threats": threats}
            for (row, col), threats in sorted(fork_cells.items())
            if threats >= 2
        ]
        return {
            "open_lines": open_lines,
            "strongest_line": strongest_line,
            "one_move_to_win": one_move_to_win,
            "fork_cells": forks,
        }

    def _candidate_lines(self, size: int, win_length: int) -> list[list[tuple[int, int]]]:
        lines = []
        for row in range(size):
            for col in range(size):
                for delta_row, delta_col in [(0, 1), (1, 0), (1, 1), (1, -1)]:
                    line = []
                    for step in range(win_length):
                        next_row = row + step * delta_row
                        next_col = col + step * delta_col
                        if next_row < 0 or next_col < 0 or next_row >= size or next_col >= size:
                            line = []
                            break
                        line.append((next_row, next_col))
                    if line:
                        lines.append(line)
        return lines

    def _strategic_zones(self, board: Board) -> dict[str, Any]:
        size = len(board)
        center_indexes = sorted({(size - 1) // 2, size // 2})
        centers = [(row, col) for row in center_indexes for col in center_indexes]
        corners = [(0, 0), (0, size - 1), (size - 1, 0), (size - 1, size - 1)]
        return {
            "available_centers": [{"row": row, "col": col} for row, col in centers if board[row][col] is None],
            "available_corners": [{"row": row, "col": col} for row, col in corners if board[row][col] is None],
        }

    def _analysis_risk(self, game_status: str, board_status: str, current_wins: list[dict[str, Any]], opponent_wins: list[dict[str, Any]]) -> str:
        if game_status == "finished" or board_status in {"win", "draw"}:
            return "finished"
        if current_wins:
            return "winning"
        if opponent_wins:
            return "danger"
        return "normal"

    def _analysis_recommendation(
        self,
        game_status: str,
        board_status: str,
        current_symbol: str,
        current_wins: list[dict[str, Any]],
        opponent_wins: list[dict[str, Any]],
        best: Any | None,
    ) -> str:
        if board_status == "win":
            return "Партия завершена победой, новые ходы недоступны."
        if game_status == "finished" or board_status == "draw":
            return "Партия завершена, можно начать реванш из комнаты."
        if current_wins:
            move = current_wins[0]
            return f"У {current_symbol} есть победный ход: строка {move['row'] + 1}, столбец {move['col'] + 1}."
        if opponent_wins:
            move = opponent_wins[0]
            return f"Нужно закрыть угрозу соперника: строка {move['row'] + 1}, столбец {move['col'] + 1}."
        if best:
            return f"Лучший ход по оценке сервера: строка {best.row + 1}, столбец {best.col + 1}."
        return "Свободных ходов нет."

    def _award_achievements(self, game: Game) -> list[dict[str, Any]]:
        unlocked: list[dict[str, Any]] = []
        for user_id in {game.player_x_id, game.player_o_id}:
            if user_id is None:
                continue
            codes = self.stats.award_automatic(user_id, game)
            for code in codes:
                unlocked.append({"user_id": user_id, "code": code})
        return unlocked

    def _room_or_404(self, room_id: int) -> Room:
        try:
            return self.rooms.get(room_id)
        except NotFoundError as exc:
            raise GameServiceError("Room not found", 404) from exc

    def _game_or_404(self, game_id: int) -> Game:
        try:
            return self.games.get(game_id)
        except NotFoundError as exc:
            raise GameServiceError("Game not found", 404) from exc

    def _ensure_game_room_is_playing(self, game: Game) -> Room:
        room = self._room_or_404(game.room_id)
        if room.status != "playing":
            raise GameServiceError("Room is not active")
        if room.current_game_id != game.id:
            raise GameServiceError("Game is not current for this room")
        return room

    def _symbol_for_user(self, game: Game, user_id: int) -> str:
        if game.player_x_id == user_id:
            return "X"
        if game.player_o_id == user_id:
            return "O"
        raise GameServiceError("User does not play this game", 403)

    def _user_for_symbol(self, game: Game, symbol: str) -> int | None:
        symbol = validate_symbol(symbol)
        return game.player_x_id if symbol == "X" else game.player_o_id
