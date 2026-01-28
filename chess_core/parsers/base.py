"""Base parser protocol and data transfer objects.

This module defines the framework-agnostic interfaces and data structures
used by all game parsers. Parsers produce GameData objects which can then
be persisted by any repository implementation.
"""

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Iterator, Protocol


@dataclass
class GameData:
    """Framework-agnostic game representation.

    This dataclass serves as a data transfer object between parsers and
    repositories. It contains all the information needed to represent
    a chess game without any framework-specific dependencies.

    Attributes:
        source_id: Unique identifier for the game (typically a hash).
        event: Name of the tournament or event.
        site: Location or platform where the game was played.
        date: Date the game was played.
        round: Round number within the event.
        white_player: Username or name of the white player.
        black_player: Username or name of the black player.
        result: Game result ("1-0", "0-1", "1/2-1/2", or "*").
        white_elo: Elo rating of white player.
        black_elo: Elo rating of black player.
        time_control: Time control setting (e.g., "300" for 5 minutes).
        termination: How the game ended (e.g., "won by resignation").
        moves: The move text in standard notation.
        source_format: Format the game was parsed from (e.g., "pgn").
        raw_headers: All original headers preserved as key-value pairs.
        opening_fen: FEN of the detected opening position (for FK lookup).
    """

    source_id: str
    event: str
    site: str
    date: date | None
    round: str | None
    white_player: str
    black_player: str
    result: str
    white_elo: int | None
    black_elo: int | None
    time_control: str | None
    termination: str | None
    moves: str
    source_format: str
    raw_headers: dict[str, str]
    opening_fen: str = ""


class GameParser(Protocol):
    """Protocol for all game parsers.

    Any parser that implements this protocol can be used with the
    GameRepository to import games from various sources.

    Example:
        >>> parser = PGNParser()
        >>> for game in parser.parse("games.pgn"):
        ...     print(f"{game.white_player} vs {game.black_player}")
    """

    def parse(self, source: Path | str) -> Iterator[GameData]:
        """Parse games from a source file or string.

        Args:
            source: Path to a file or a string containing game data.

        Yields:
            GameData objects for each game found in the source.
        """
        ...
