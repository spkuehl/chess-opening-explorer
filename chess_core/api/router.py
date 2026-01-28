"""API router for chess games endpoints."""

from ninja import NinjaAPI, Query

from chess_core.api.schemas import (
    OpeningStatsFilterSchema,
    OpeningStatsResponse,
    OpeningStatsSchema,
)
from chess_core.services.opening_stats import OpeningStatsFilterParams, OpeningStatsService

api = NinjaAPI(
    title="Chess Explorer API",
    version="1.0.0",
    description="API for exploring chess games and opening statistics.",
    urls_namespace="api-v1",
)


@api.get(
    "/openings/stats/",
    response=OpeningStatsResponse,
    summary="Get opening statistics",
    description=(
        "Returns aggregated statistics for chess openings including game counts, "
        "win/draw/loss distribution, and average move counts. Results can be "
        "filtered by player, ECO code, opening name, date range, ELO range, and "
        "minimum game threshold."
    ),
    tags=["openings"],
)
def get_opening_stats(
    request,
    filters: OpeningStatsFilterSchema = Query(...),
) -> OpeningStatsResponse:
    """Get aggregated opening statistics with optional filters.

    Args:
        request: HTTP request object.
        filters: Query parameters for filtering results.

    Returns:
        OpeningStatsResponse with list of opening statistics and total count.
    """
    service = OpeningStatsService()

    # Convert API schema to service filter params
    filter_params = OpeningStatsFilterParams(
        white_player=filters.white_player,
        black_player=filters.black_player,
        any_player=filters.any_player,
        eco_code=filters.eco_code,
        opening_name=filters.opening_name,
        date_from=filters.date_from,
        date_to=filters.date_to,
        white_elo_min=filters.white_elo_min,
        white_elo_max=filters.white_elo_max,
        black_elo_min=filters.black_elo_min,
        black_elo_max=filters.black_elo_max,
        threshold=filters.threshold,
    )

    results = list(service.get_stats(filter_params))

    # Transform query results to response schema
    items = [
        OpeningStatsSchema(
            eco_code=r["opening__eco_code"],
            name=r["opening__name"],
            moves=r["opening__moves"],
            game_count=r["game_count"],
            white_wins=r["white_wins"],
            draws=r["draws"],
            black_wins=r["black_wins"],
            avg_moves=round(r["avg_moves"], 2) if r["avg_moves"] else None,
        )
        for r in results
    ]

    return OpeningStatsResponse(items=items, total=len(items))
