from __future__ import annotations

from typing import Any

from ..repositories import GameRepository, RoomRepository, StatsRepository, UserRepository


class StatisticsService:
    def __init__(self) -> None:
        self.stats = StatsRepository()
        self.users = UserRepository()
        self.rooms = RoomRepository()
        self.games = GameRepository()

    def leaderboard(self, limit: int = 20) -> list[dict[str, Any]]:
        rows = self.stats.leaderboard(limit)
        return [self._with_rates(row) for row in rows]

    def user_dashboard(self, user_id: int) -> dict[str, Any]:
        user = self.users.get_by_id(user_id)
        stats = self.stats.get(user_id)
        achievements = self.stats.achievements(user_id)
        return {
            "user": user.public(),
            "stats": stats.public(),
            "achievements": [achievement.__dict__ for achievement in achievements],
            "recent_games": self.recent_games(user_id, 5),
        }

    def achievement_catalog(self) -> list[dict[str, Any]]:
        return self.stats.achievement_catalog()

    def recent_games(self, user_id: int, limit: int = 10) -> list[dict[str, Any]]:
        self.users.get_by_id(user_id)
        rows = self.games.recent_for_user(user_id, limit)
        return [self._decorate_recent_game(row, user_id) for row in rows]

    def global_summary(self) -> dict[str, Any]:
        rooms = self.rooms.list(limit=100)
        games = []
        for room in rooms:
            games.extend(self.games.list_for_room(room.id))
        finished = [game for game in games if game.status == "finished"]
        draws = [game for game in finished if game.draw]
        return {
            "rooms_total": len(rooms),
            "rooms_waiting": len([room for room in rooms if room.status == "waiting"]),
            "rooms_playing": len([room for room in rooms if room.status == "playing"]),
            "games_total": len(games),
            "games_finished": len(finished),
            "draws": len(draws),
        }

    def _with_rates(self, row: dict[str, Any]) -> dict[str, Any]:
        games_played = max(int(row.get("games_played", 0)), 1)
        row = row.copy()
        row["win_rate"] = round(int(row.get("wins", 0)) / games_played, 4)
        row["loss_rate"] = round(int(row.get("losses", 0)) / games_played, 4)
        row["draw_rate"] = round(int(row.get("draws", 0)) / games_played, 4)
        return row

    def _decorate_recent_game(self, row: dict[str, Any], user_id: int) -> dict[str, Any]:
        row = row.copy()
        if row.get("draw"):
            result = "draw"
        elif row.get("winner_user_id") == user_id:
            result = "win"
        elif row.get("winner_user_id") is None:
            result = "in_progress" if row.get("status") == "playing" else "unknown"
        else:
            result = "loss"
        opponent_username = row.get("player_o_username") if row.get("player_x_id") == user_id else row.get("player_x_username")
        row["result_for_user"] = result
        row["opponent_username"] = opponent_username or "AI"
        return row
