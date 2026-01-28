"""Repository for persisting chess games to the database.

This module provides the GameRepository class which bridges the gap between
framework-agnostic GameData objects and Django ORM models.
"""

from collections.abc import Iterable
from typing import Any

from .models import Game, Opening
from .parsers.base import GameData


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
        # Resolve opening FEN to Opening ID
        opening_id = None
        if game_data.opening_fen:
            opening_id = self._opening_cache.get(game_data.opening_fen)

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
            "source_format": game_data.source_format,
            "raw_headers": game_data.raw_headers,
            "opening_id": opening_id,
        }

    def _flush_batch(self, batch: list[Game]) -> None:
        """Write a batch of games to the database.

        Args:
            batch: List of Game model instances to save.
        """
        Game.objects.bulk_create(batch, ignore_conflicts=True)
