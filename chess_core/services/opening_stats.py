"""Opening statistics service for aggregating game data by opening."""

from dataclasses import dataclass
from datetime import date

from django.db.models import Avg, Count, ExpressionWrapper, F, FloatField, Q, QuerySet
from django.db.models.functions import Coalesce, NullIf

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
        opening_threshold: If set, only include openings with ply_count
            greater than or equal to this value.
        sort_by: Field to sort by (eco_code, name, moves, game_count,
            white_wins, draws, black_wins, white_pct, draw_pct, black_pct,
            avg_moves).
        order: Sort direction ("asc" or "desc").
        page: 1-based page number.
        page_size: Number of results per page (capped by PAGE_SIZE_MAX).
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
    page: int = 1
    page_size: int = 10


PAGE_SIZE_MAX = 100


ALLOWED_SORT_FIELDS = frozenset(
    {
        "eco_code",
        "name",
        "moves",
        "game_count",
        "white_wins",
        "draws",
        "black_wins",
        "white_pct",
        "draw_pct",
        "black_pct",
        "avg_moves",
    }
)

SORT_FIELD_TO_QUERY = {
    "eco_code": "opening__eco_code",
    "name": "opening__name",
    "moves": "opening__moves",
    "game_count": "game_count",
    "white_wins": "white_wins",
    "draws": "draws",
    "black_wins": "black_wins",
    "white_pct": "white_pct",
    "draw_pct": "draw_pct",
    "black_pct": "black_pct",
    "avg_moves": "avg_moves",
}


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

    def get_stats(self, filters: OpeningStatsFilterParams) -> tuple[list[dict], int]:
        """Get a page of aggregated opening statistics with optional filters.

        Builds an optimized query that filters, aggregates, sorts, then
        returns one page of results and the total count.

        Args:
            filters: Filter parameters including page and page_size.

        Returns:
            Tuple of (page_items, total_count). page_items is a list of dicts
            with opening__eco_code, opening__name, opening__moves, game_count,
            white_wins, draws, black_wins, avg_moves. total_count is the
            number of openings matching the filters (all pages).
        """
        qs = self._build_base_query()
        qs = self._apply_filters(qs, filters)
        qs = self._apply_aggregation(qs)
        qs = self._apply_threshold(qs, filters.threshold)
        qs = self._apply_percentage_annotations(qs)
        qs = self._apply_sort(qs, filters)
        total_count = qs.count()
        page = max(1, filters.page)
        page_size = min(PAGE_SIZE_MAX, max(1, filters.page_size))
        start = (page - 1) * page_size
        page_qs = qs[start : start + page_size]
        items = list(page_qs)
        for row in items:
            row["white_pct"], row["draw_pct"], row["black_pct"] = (
                self._result_percentages(
                    row["game_count"],
                    row["white_wins"],
                    row["draws"],
                    row["black_wins"],
                )
            )
        return items, total_count

    def _result_percentages(
        self,
        game_count: int,
        white_wins: int,
        draws: int,
        black_wins: int,
    ) -> tuple[float, float, float]:
        """Normalized win/draw/loss percentages (0–100) for white, draw, black.

        When game_count is 0, returns (0.0, 0.0, 0.0).
        """
        if game_count <= 0:
            return (0.0, 0.0, 0.0)
        scale = 100.0 / game_count
        return (
            round(white_wins * scale, 2),
            round(draws * scale, 2),
            round(black_wins * scale, 2),
        )

    def _build_base_query(self) -> QuerySet:
        """Build base query excluding games without openings."""
        return Game.objects.filter(opening__isnull=False)

    def _apply_filters(
        self, qs: QuerySet, filters: OpeningStatsFilterParams
    ) -> QuerySet:
        """Apply all filter conditions to the query."""
        qs = self._apply_player_filters(qs, filters)
        qs = self._apply_opening_filters(qs, filters)
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

    def _apply_opening_filters(
        self, qs: QuerySet, filters: OpeningStatsFilterParams
    ) -> QuerySet:
        """Apply opening-based filters such as ECO code and name."""
        if filters.eco_code:
            qs = qs.filter(opening__eco_code=filters.eco_code)
        if filters.opening_name:
            qs = qs.filter(opening__name__icontains=filters.opening_name)
        if filters.opening_threshold is not None:
            qs = qs.filter(opening__ply_count__gte=filters.opening_threshold)
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
        return qs.values(
            "opening_id",
            "opening__eco_code",
            "opening__name",
            "opening__moves",
        ).annotate(
            game_count=Count("id"),
            white_wins=Count("id", filter=Q(result="1-0")),
            draws=Count("id", filter=Q(result="1/2-1/2")),
            black_wins=Count("id", filter=Q(result="0-1")),
            avg_moves=Avg("move_count_ply")
            / 2.0,  # Divide by 2 to get the game's move number, not ply.
        )

    def _apply_threshold(self, qs: QuerySet, threshold: int) -> QuerySet:
        """Apply minimum game count threshold (HAVING clause)."""
        if threshold > 0:
            qs = qs.filter(game_count__gte=threshold)
        return qs

    def _apply_percentage_annotations(self, qs: QuerySet) -> QuerySet:
        """Annotate white_pct, draw_pct, black_pct (0–100) for sorting."""
        denom = Coalesce(NullIf(F("game_count"), 0), 1)
        return qs.annotate(
            white_pct=ExpressionWrapper(
                F("white_wins") * 100.0 / denom, output_field=FloatField()
            ),
            draw_pct=ExpressionWrapper(
                F("draws") * 100.0 / denom, output_field=FloatField()
            ),
            black_pct=ExpressionWrapper(
                F("black_wins") * 100.0 / denom, output_field=FloatField()
            ),
        )

    def _apply_sort(self, qs: QuerySet, filters: OpeningStatsFilterParams) -> QuerySet:
        """Apply ordering by sort_by and order, defaulting to game_count desc."""
        sort_by = filters.sort_by
        order = (filters.order or "desc").lower()
        if order not in ("asc", "desc"):
            order = "desc"
        if not sort_by or sort_by not in ALLOWED_SORT_FIELDS:
            return qs.order_by("-game_count")
        query_field = SORT_FIELD_TO_QUERY[sort_by]
        prefix = "-" if order == "desc" else ""
        return qs.order_by(f"{prefix}{query_field}")
