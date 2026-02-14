"""Repository for persisting chess games to the database.

This module provides the GameRepository class which bridges the gap between
framework-agnostic GameData objects and Django ORM models.
"""

from collections.abc import Iterable
from typing import Any

from .models import Game, Opening
from .parsers.base import GameData
from .services import EndgameDetector, OpeningDetector


class GameRepository:
    """Handles persistence of games to the database.

    This repository provides methods for saving games individually or in
    batches, with support for deduplication based on source_id.

    Example:
        >>> repo = GameRepository()
        >>> parser = PGNParser()
        >>> count = repo.save_batch(parser.parse("games.pgn"))
        >>> print(f"Imported {count} games")
    """

    def __init__(self) -> None:
        """Initialize the repository with opening FEN cache."""
        # Pre-load FEN → Opening ID mapping for efficient bulk inserts
        self._opening_cache: dict[str, int] = dict(
            Opening.objects.values_list("fen", "id")
        )

    def save(self, game_data: GameData) -> Game:
        """Save a single game, updating if source_id exists.

        Args:
            game_data: The game data to save.

        Returns:
            The saved Game model instance.
        """
        game, _ = Game.objects.update_or_create(
            source_id=game_data.source_id,
            defaults=self._to_model_fields(game_data),
        )
        return game

    def save_batch(
        self,
        games: Iterable[GameData],
        batch_size: int = 1000,
    ) -> int:
        """Bulk insert games, skipping duplicates.

        Uses Django's bulk_create with ignore_conflicts for efficient
        batch insertion. Existing games (by source_id) are skipped.

        Args:
            games: Iterable of GameData objects to save.
            batch_size: Number of games to insert per batch.

        Returns:
            The total number of games processed.
        """
        batch: list[Game] = []
        total_processed = 0

        for game_data in games:
            model = Game(
                source_id=game_data.source_id,
                **self._to_model_fields(game_data),
            )
            batch.append(model)
            total_processed += 1

            if len(batch) >= batch_size:
                self._flush_batch(batch)
                batch = []

        # Flush remaining games
        if batch:
            self._flush_batch(batch)

        return total_processed

    def exists(self, source_id: str) -> bool:
        """Check if a game with the given source_id exists.

        Args:
            source_id: The unique identifier to check.

        Returns:
            True if a game with this source_id exists, False otherwise.
        """
        return Game.objects.filter(source_id=source_id).exists()

    def count(self) -> int:
        """Return the total number of games in the database.

        Returns:
            The count of all games.
        """
        return Game.objects.count()

    def _to_model_fields(self, game_data: GameData) -> dict[str, Any]:
        """Convert GameData to a dictionary of model fields.

        Args:
            game_data: The game data to convert.

        Returns:
            Dictionary of field names to values for the Game model.
        """
        # Detect opening from moves and resolve FEN to Opening ID
        match = OpeningDetector().detect_opening(game_data.moves)
        opening_id = self._opening_cache.get(match.fen) if match else None

        endgame_entry = EndgameDetector().detect_endgame(game_data.moves)
        if endgame_entry is not None:
            endgame_move_ply = endgame_entry.ply
            endgame_fen = (
                endgame_entry.fen[:100]
                if len(endgame_entry.fen) > 100
                else endgame_entry.fen
            )
        else:
            endgame_move_ply = None
            endgame_fen = None

        return {
            "event": game_data.event,
            "site": game_data.site,
            "date": game_data.date,
            "round": game_data.round or "",
            "white_player": game_data.white_player,
            "black_player": game_data.black_player,
            "result": game_data.result,
            "white_elo": game_data.white_elo,
            "black_elo": game_data.black_elo,
            "time_control": game_data.time_control or "",
            "termination": game_data.termination or "",
            "moves": game_data.moves,
            "move_count_ply": self._count_moves(game_data.moves),
            "source_format": game_data.source_format,
            "raw_headers": game_data.raw_headers,
            "opening_id": opening_id,
            "endgame_move_ply": endgame_move_ply,
            "endgame_fen": endgame_fen,
        }

    def _count_moves(self, moves: str) -> int | None:
        """Count the number of half-moves (ply) in a move string.

        Args:
            moves: A move string in SAN format, e.g., "1. e4 e5 2. Nf3 Nc6".

        Returns:
            The number of half-moves (ply), or None if moves is empty.
        """
        if not moves:
            return None

        tokens = moves.split()
        move_count = 0

        for token in tokens:
            # Skip move numbers (e.g., "1.", "2.", "1...")
            if token.endswith(".") or token.replace(".", "").isdigit():
                continue
            # Skip result markers
            if token in ("1-0", "0-1", "1/2-1/2", "*"):
                continue
            move_count += 1

        return move_count if move_count > 0 else None

    def _flush_batch(self, batch: list[Game]) -> None:
        """Write a batch of games to the database.

        Args:
            batch: List of Game model instances to save.
        """
        Game.objects.bulk_create(batch, ignore_conflicts=True)
