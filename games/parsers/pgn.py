"""PGN file parser implementation.

This module provides a parser for PGN (Portable Game Notation) files,
the standard format for recording chess games.
"""

from __future__ import annotations

import hashlib
from datetime import date
from pathlib import Path
from typing import TYPE_CHECKING, Iterator

import chess.pgn

from .base import GameData

if TYPE_CHECKING:
    from games.services.openings import OpeningDetector


class PGNParser:
    """Parser for PGN (Portable Game Notation) files.

    Uses the python-chess library to parse PGN files and yields
    GameData objects for each game found.

    Example:
        >>> parser = PGNParser()
        >>> for game in parser.parse("tournament.pgn"):
        ...     print(f"{game.white_player} vs {game.black_player}: {game.result}")
    """

    def __init__(self, opening_detector: OpeningDetector | None = None) -> None:
        """Initialize the parser.

        Args:
            opening_detector: Optional detector to identify openings in games.
        """
        self._opening_detector = opening_detector

    def parse(self, source: Path | str) -> Iterator[GameData]:
        """Parse games from a PGN file.

        Args:
            source: Path to the PGN file.

        Yields:
            GameData objects for each game in the file.
        """
        path = Path(source)
        with open(path, encoding="utf-8", errors="replace") as pgn_file:
            while True:
                game = chess.pgn.read_game(pgn_file)
                if game is None:
                    break

                game_data = self._convert_game(game)
                if game_data is not None:
                    yield game_data

    def _convert_game(self, game: chess.pgn.Game) -> GameData | None:
        """Convert a python-chess Game to a GameData object.

        Args:
            game: A python-chess Game object.

        Returns:
            A GameData object, or None if the game is invalid.
        """
        headers = game.headers

        # Extract required fields
        white_player = headers.get("White", "Unknown")
        black_player = headers.get("Black", "Unknown")
        result = headers.get("Result", "*")

        # Generate a unique source_id from key headers
        source_id = self._generate_source_id(headers)

        # Parse date
        game_date = self._parse_date(headers.get("Date", ""))

        # Parse Elo ratings
        white_elo = self._parse_int(headers.get("WhiteElo"))
        black_elo = self._parse_int(headers.get("BlackElo"))

        # Get move text (without clock annotations for cleaner storage)
        moves = self._get_moves_text(game)

        # Collect all raw headers
        raw_headers = dict(headers)

        # Detect opening if detector is available
        opening_fen = ""
        if self._opening_detector:
            match = self._opening_detector.detect_opening(moves)
            if match:
                opening_fen = match.fen

        return GameData(
            source_id=source_id,
            event=headers.get("Event", ""),
            site=headers.get("Site", ""),
            date=game_date,
            round=headers.get("Round"),
            white_player=white_player,
            black_player=black_player,
            result=result,
            white_elo=white_elo,
            black_elo=black_elo,
            time_control=headers.get("TimeControl"),
            termination=headers.get("Termination"),
            moves=moves,
            source_format="pgn",
            raw_headers=raw_headers,
            opening_fen=opening_fen,
        )

    def _generate_source_id(self, headers: chess.pgn.Headers) -> str:
        """Generate a unique ID for a game based on its headers.

        Args:
            headers: The PGN headers.

        Returns:
            A SHA-256 hash of key identifying information.
        """
        # Use key headers that should uniquely identify a game
        key_parts = [
            headers.get("Event", ""),
            headers.get("Site", ""),
            headers.get("Date", ""),
            headers.get("Round", ""),
            headers.get("White", ""),
            headers.get("Black", ""),
            headers.get("Result", ""),
            # Include end time if available for uniqueness in same-round games
            headers.get("EndTime", ""),
        ]
        key_string = "|".join(key_parts)
        return hashlib.sha256(key_string.encode()).hexdigest()[:64]

    def _parse_date(self, date_str: str) -> date | None:
        """Parse a PGN date string to a Python date.

        PGN dates are in format YYYY.MM.DD, but may have unknown parts
        represented as "??".

        Args:
            date_str: The date string from PGN headers.

        Returns:
            A date object if parseable, None otherwise.
        """
        if not date_str or "?" in date_str:
            # Try to parse partial dates
            parts = date_str.split(".")
            if len(parts) == 3:
                try:
                    year = int(parts[0]) if parts[0] != "????" else None
                    month = int(parts[1]) if parts[1] != "??" else 1
                    day = int(parts[2]) if parts[2] != "??" else 1
                    if year:
                        return date(year, month, day)
                except (ValueError, TypeError):
                    pass
            return None

        try:
            parts = date_str.split(".")
            if len(parts) == 3:
                return date(int(parts[0]), int(parts[1]), int(parts[2]))
        except (ValueError, IndexError):
            pass
        return None

    def _parse_int(self, value: str | None) -> int | None:
        """Safely parse a string to an integer.

        Args:
            value: String to parse.

        Returns:
            Integer value or None if parsing fails.
        """
        if not value or value == "?" or value == "-":
            return None
        try:
            return int(value)
        except ValueError:
            return None

    def _get_moves_text(self, game: chess.pgn.Game) -> str:
        """Extract the move text from a game.

        Args:
            game: A python-chess Game object.

        Returns:
            The moves as a string in standard algebraic notation.
        """
        # Use the exporter to get clean move text
        exporter = chess.pgn.StringExporter(
            headers=False, variations=False, comments=False
        )
        return game.accept(exporter).strip()
