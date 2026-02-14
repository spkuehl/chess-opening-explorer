"""API router for chess games endpoints."""

from django.http import Http404

from ninja import NinjaAPI, Query

from chess_core.api.schemas import (
    LatestGameSchema,
    OpeningGameDetailsSchema,
    OpeningStatsFilterSchema,
    OpeningStatsResponse,
    OpeningStatsSchema,
    WinRateOverTimeFilterSchema,
    WinRateOverTimePointSchema,
    WinRateOverTimeResponseSchema,
)
from chess_core.services.latest_game import get_latest_game_for_opening
from chess_core.services.opening_game_details import get_opening_game_details
from chess_core.services.opening_stats import (
    OpeningStatsFilterParams,
    OpeningStatsService,
)
from chess_core.services.win_rate_over_time import (
    WinRateOverTimeFilterParams,
    get_win_rate_over_time,
)

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
        opening_threshold=filters.opening_threshold,
        sort_by=filters.sort_by,
        order=filters.order,
        page=filters.page,
        page_size=filters.page_size,
    )

    results, total_count = service.get_stats(filter_params)

    # Transform query results to response schema
    items = [
        OpeningStatsSchema(
            opening_id=r["opening_id"],
            eco_code=r["opening__eco_code"],
            name=r["opening__name"],
            moves=r["opening__moves"],
            game_count=r["game_count"],
            white_wins=r["white_wins"],
            draws=r["draws"],
            black_wins=r["black_wins"],
            white_pct=r["white_pct"],
            draw_pct=r["draw_pct"],
            black_pct=r["black_pct"],
            avg_moves=round(r["avg_moves"], 2) if r["avg_moves"] else None,
        )
        for r in results
    ]

    return OpeningStatsResponse(items=items, total=total_count)


@api.get(
    "/openings/{opening_id}/latest-game/",
    response=LatestGameSchema,
    summary="Get latest game for opening",
    description=(
        "Returns the most recent game (by date, then id) for the given opening. "
        "Responds with 404 if the opening has no games or the opening_id is invalid."
    ),
    tags=["openings"],
)
def get_latest_game_for_opening_endpoint(request, opening_id: int) -> LatestGameSchema:
    """Get the most recent game for an opening by opening id."""
    game = get_latest_game_for_opening(opening_id)
    if game is None:
        raise Http404("No game found for this opening.")
    return LatestGameSchema(
        id=game.id,
        source_id=game.source_id,
        event=game.event or "",
        site=game.site or "",
        date=game.date,
        round=game.round or "",
        white_player=game.white_player,
        black_player=game.black_player,
        result=game.result,
        white_elo=game.white_elo,
        black_elo=game.black_elo,
        time_control=game.time_control or "",
        termination=game.termination or "",
        moves=game.moves,
    )


@api.get(
    "/openings/{opening_id}/game-details/",
    response=OpeningGameDetailsSchema,
    summary="Get opening game details",
    description=(
        "Returns aggregate game details for one opening: game counts, "
        "win/draw/loss counts, and average move number when white wins and "
        "when black wins. 404 if the opening has no games or is invalid."
    ),
    tags=["openings"],
)
def get_opening_game_details_endpoint(
    request, opening_id: int
) -> OpeningGameDetailsSchema:
    """Get game detail aggregates for an opening by opening id."""
    details = get_opening_game_details(opening_id)
    if details is None:
        raise Http404("No game details for this opening.")
    return OpeningGameDetailsSchema(**details)


@api.get(
    "/stats/win-rate-over-time/",
    response=WinRateOverTimeResponseSchema,
    summary="Get win rate over time",
    description=(
        "Returns time-series points of white/draw/black win percentages by period "
        "(week, month, or year). X axis is Game.date. Optional filters: date range, "
        "opening, player, ELO, min_games per period."
    ),
    tags=["stats"],
)
def get_win_rate_over_time_endpoint(
    request,
    filters: WinRateOverTimeFilterSchema = Query(...),
) -> WinRateOverTimeResponseSchema:
    """Get win rate over time for stacked line chart."""
    params = WinRateOverTimeFilterParams(
        period=filters.period,
        date_from=filters.date_from,
        date_to=filters.date_to,
        eco_code=filters.eco_code,
        opening_id=filters.opening_id,
        opening_name=filters.opening_name,
        any_player=filters.any_player,
        white_player=filters.white_player,
        black_player=filters.black_player,
        white_elo_min=filters.white_elo_min,
        white_elo_max=filters.white_elo_max,
        black_elo_min=filters.black_elo_min,
        black_elo_max=filters.black_elo_max,
        min_games=filters.min_games,
        opening_threshold=filters.opening_threshold,
    )
    items_raw = get_win_rate_over_time(params)
    items = [WinRateOverTimePointSchema(**r) for r in items_raw]
    return WinRateOverTimeResponseSchema(items=items)
