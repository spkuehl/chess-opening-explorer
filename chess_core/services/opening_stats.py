"""Opening statistics service for aggregating game data by opening."""

from dataclasses import dataclass
from datetime import date

from django.db.models import Avg, Count, Q, QuerySet

from chess_core.models import Game


@dataclass
class OpeningStatsFilterParams:
    """Filter parameters for opening statistics queries.

    All fields are optional with sensible defaults. Use None for unbounded
    range filters.

    Attributes:
        white_player: Filter games where white player name contains value.
        black_player: Filter games where black player name contains value.
        any_player: Filter games where either player contains value (OR).
            Takes precedence over white_player/black_player if provided.
        date_from: Lower bound for game date (inclusive).
        date_to: Upper bound for game date (inclusive).
        white_elo_min: Minimum white player ELO.
        white_elo_max: Maximum white player ELO.
        black_elo_min: Minimum black player ELO.
        black_elo_max: Maximum black player ELO.
        threshold: Minimum game count required for opening to appear in results.
    """

    white_player: str | None = None
    black_player: str | None = None
    any_player: str | None = None
    date_from: date | None = None
    date_to: date | None = None
    white_elo_min: int | None = None
    white_elo_max: int | None = None
    black_elo_min: int | None = None
    black_elo_max: int | None = None
    threshold: int = 1


class OpeningStatsService:
    """Service for aggregating game statistics by opening.

    Provides optimized queries for calculating win/draw/loss rates and
    average move counts grouped by chess opening.

    Example:
        >>> service = OpeningStatsService()
        >>> filters = OpeningStatsFilterParams(any_player="Carlsen", threshold=5)
        >>> for stats in service.get_stats(filters):
        ...     print(f"{stats['opening__name']}: {stats['game_count']} games")
    """

    def get_stats(self, filters: OpeningStatsFilterParams) -> QuerySet:
        """Get aggregated opening statistics with optional filters.

        Builds an optimized query that:
        - Excludes games without an opening
        - Applies all specified filters
        - Groups by opening (eco_code, name)
        - Calculates game counts, results, and average moves
        - Applies threshold filter via HAVING clause
        - Orders by game count descending

        Args:
            filters: Filter parameters for the query.

        Returns:
            QuerySet of dictionaries with aggregated stats per opening.
            Each dict contains: opening__eco_code, opening__name, game_count,
            white_wins, draws, black_wins, avg_moves.
        """
        qs = self._build_base_query()
        qs = self._apply_filters(qs, filters)
        qs = self._apply_aggregation(qs)
        qs = self._apply_threshold(qs, filters.threshold)
        return qs.order_by("-game_count")

    def _build_base_query(self) -> QuerySet:
        """Build base query excluding games without openings."""
        return Game.objects.filter(opening__isnull=False)

    def _apply_filters(
        self, qs: QuerySet, filters: OpeningStatsFilterParams
    ) -> QuerySet:
        """Apply all filter conditions to the query."""
        qs = self._apply_player_filters(qs, filters)
        qs = self._apply_date_filters(qs, filters)
        qs = self._apply_elo_filters(qs, filters)
        return qs

    def _apply_player_filters(
        self, qs: QuerySet, filters: OpeningStatsFilterParams
    ) -> QuerySet:
        """Apply player name filters.

        any_player takes precedence and uses OR logic.
        white_player and black_player use AND logic when both specified.
        """
        if filters.any_player:
            qs = qs.filter(
                Q(white_player__icontains=filters.any_player)
                | Q(black_player__icontains=filters.any_player)
            )
        else:
            if filters.white_player:
                qs = qs.filter(white_player__icontains=filters.white_player)
            if filters.black_player:
                qs = qs.filter(black_player__icontains=filters.black_player)
        return qs

    def _apply_date_filters(
        self, qs: QuerySet, filters: OpeningStatsFilterParams
    ) -> QuerySet:
        """Apply game date range filters."""
        if filters.date_from:
            qs = qs.filter(date__gte=filters.date_from)
        if filters.date_to:
            qs = qs.filter(date__lte=filters.date_to)
        return qs

    def _apply_elo_filters(
        self, qs: QuerySet, filters: OpeningStatsFilterParams
    ) -> QuerySet:
        """Apply ELO range filters for both white and black players."""
        if filters.white_elo_min is not None:
            qs = qs.filter(white_elo__gte=filters.white_elo_min)
        if filters.white_elo_max is not None:
            qs = qs.filter(white_elo__lte=filters.white_elo_max)
        if filters.black_elo_min is not None:
            qs = qs.filter(black_elo__gte=filters.black_elo_min)
        if filters.black_elo_max is not None:
            qs = qs.filter(black_elo__lte=filters.black_elo_max)
        return qs

    def _apply_aggregation(self, qs: QuerySet) -> QuerySet:
        """Apply grouping and aggregation functions.

        Groups by opening and calculates:
        - game_count: Total games for this opening
        - white_wins: Count of games where result is "1-0"
        - draws: Count of games where result is "1/2-1/2"
        - black_wins: Count of games where result is "0-1"
        - avg_moves: Average move_count across games
        """
        return qs.values("opening__eco_code", "opening__name", "opening__moves").annotate(
            game_count=Count("id"),
            white_wins=Count("id", filter=Q(result="1-0")),
            draws=Count("id", filter=Q(result="1/2-1/2")),
            black_wins=Count("id", filter=Q(result="0-1")),
            avg_moves=Avg("move_count_ply") / 2.0, # Divide by 2 to get the game's move number, not ply.
        )

    def _apply_threshold(self, qs: QuerySet, threshold: int) -> QuerySet:
        """Apply minimum game count threshold (HAVING clause)."""
        if threshold > 0:
            qs = qs.filter(game_count__gte=threshold)
        return qs
