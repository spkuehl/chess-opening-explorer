"""Pydantic schemas for Opening Stats API."""

from datetime import date

from ninja import Schema


class OpeningStatsSchema(Schema):
    """Response schema for individual opening statistics.

    Attributes:
        eco_code: ECO classification code (e.g., "B20").
        name: Opening name (e.g., "Sicilian Defense").
        moves: Opening move sequence (e.g., "1. e4 c5").
        game_count: Total number of games with this opening.
        white_wins: Number of games won by white (result "1-0").
        draws: Number of drawn games (result "1/2-1/2").
        black_wins: Number of games won by black (result "0-1").
        avg_moves: Average number of moves per game.
    """

    eco_code: str
    name: str
    moves: str
    game_count: int
    white_wins: int
    draws: int
    black_wins: int
    avg_moves: float | None


class OpeningStatsResponse(Schema):
    """Response wrapper for opening statistics list.

    Attributes:
        items: List of opening statistics.
        total: Total count of openings in the response.
    """

    items: list[OpeningStatsSchema]
    total: int


class OpeningStatsFilterSchema(Schema):
    """Query parameters for filtering opening statistics.

    All fields are optional. Use None for unbounded range filters.

    Attributes:
        white_player: Filter games where white player name contains value.
        black_player: Filter games where black player name contains value.
        any_player: Filter games where either player contains value (OR).
            Takes precedence over white_player/black_player if provided.
        eco_code: Filter by exact ECO code (e.g. "B20").
        opening_name: Filter openings whose name contains the given text
            (case-insensitive).
        date_from: Lower bound for game date (inclusive).
        date_to: Upper bound for game date (inclusive).
        white_elo_min: Minimum white player ELO.
        white_elo_max: Maximum white player ELO.
        black_elo_min: Minimum black player ELO.
        black_elo_max: Maximum black player ELO.
        threshold: Minimum game count required for opening to appear in
            results.
    """

    white_player: str | None = None
    black_player: str | None = None
    any_player: str | None = None
    eco_code: str | None = None
    opening_name: str | None = None
    date_from: date | None = None
    date_to: date | None = None
    white_elo_min: int | None = None
    white_elo_max: int | None = None
    black_elo_min: int | None = None
    black_elo_max: int | None = None
    threshold: int = 1
