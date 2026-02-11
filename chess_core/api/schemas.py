"""Pydantic schemas for Opening Stats API."""

from datetime import date
from typing import Literal

from ninja import Schema
from pydantic import Field


class LatestGameSchema(Schema):
    """Response schema for the most recent game of an opening.

    Attributes:
        id: Game primary key.
        source_id: Unique identifier from the source (e.g. PGN).
        event: Event name.
        site: Site name.
        date: Game date.
        round: Round designation.
        white_player: White player name.
        black_player: Black player name.
        result: Game result (e.g. "1-0", "1/2-1/2", "0-1").
        white_elo: White player ELO (optional).
        black_elo: Black player ELO (optional).
        time_control: Time control string.
        termination: Termination description.
        moves: Game moves in standard notation.
    """

    id: int
    source_id: str
    event: str
    site: str
    date: date | None
    round: str
    white_player: str
    black_player: str
    result: str
    white_elo: int | None
    black_elo: int | None
    time_control: str
    termination: str
    moves: str


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
        white_pct: Percentage of games won by white (0–100).
        draw_pct: Percentage of drawn games (0–100).
        black_pct: Percentage of games won by black (0–100).
        avg_moves: Average number of moves per game.
        opening_id: Primary key of the opening (for linking to latest-game).
    """

    opening_id: int
    eco_code: str
    name: str
    moves: str
    game_count: int
    white_wins: int
    draws: int
    black_wins: int
    white_pct: float
    draw_pct: float
    black_pct: float
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
        opening_threshold: If set, only openings with ply_count greater
            than or equal to this value.
        sort_by: Field to sort by (eco_code, name, moves, game_count, etc.).
        order: Sort direction ("asc" or "desc").
        page: 1-based page number.
        page_size: Results per page (max 100).
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
    opening_threshold: int | None = None
    sort_by: str | None = None
    order: str | None = None
    page: int = Field(1, ge=1)
    page_size: int = Field(10, ge=1, le=100)


class WinRateOverTimePointSchema(Schema):
    """One time-series point for win rate over time.

    Attributes:
        period: Canonical period id (e.g. 2024-W01, 2024-01, 2024).
        period_label: Date stamp for the period (same as period, e.g. 2024-W01).
        white_pct: Percentage of games won by white (0–100).
        draw_pct: Percentage of drawn games (0–100).
        black_pct: Percentage of games won by black (0–100).
        game_count: Number of games in the period.
    """

    period: str
    period_label: str
    white_pct: float
    draw_pct: float
    black_pct: float
    game_count: int


class WinRateOverTimeResponseSchema(Schema):
    """Response for win-rate-over-time endpoint.

    Attributes:
        items: Time-series points ordered by period ascending.
    """

    items: list[WinRateOverTimePointSchema]


class WinRateOverTimeFilterSchema(Schema):
    """Query parameters for win-rate-over-time.

    period: week, month, or year (default week). Rest optional.
    """

    period: Literal["week", "month", "year"] = "week"
    date_from: date | None = None
    date_to: date | None = None
    eco_code: str | None = None
    opening_id: int | None = None
    opening_name: str | None = None
    any_player: str | None = None
    white_player: str | None = None
    black_player: str | None = None
    white_elo_min: int | None = None
    white_elo_max: int | None = None
    black_elo_min: int | None = None
    black_elo_max: int | None = None
    min_games: int = 1
    opening_threshold: int | None = None
