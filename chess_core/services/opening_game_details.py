"""Service for per-opening game detail aggregates (e.g. average move number by result)."""

from django.db.models import Avg, Count, ExpressionWrapper, F, FloatField, Q, QuerySet

from chess_core.models import Game, Opening


def get_opening_game_details(opening_id: int) -> dict | None:
    """Return aggregate game details for one opening, or None if no games.

    Only includes games with non-null move_count_ply. Average move numbers
    are full moves (1, 2, 3...): white wins end on white's move, black wins
    on black's move.

    Args:
        opening_id: Primary key of the Opening.

    Returns:
        Dict with opening_id, eco_code, name, moves, game_count, white_wins,
        draws, black_wins, avg_move_number_white_wins, avg_move_number_black_wins,
        games_reaching_endgame, pct_reaches_endgame, avg_move_number_endgame.
        None if the opening does not exist or has no games with move_count_ply.
    """
    try:
        opening = Opening.objects.get(pk=opening_id)
    except Opening.DoesNotExist:
        return None

    qs: QuerySet[Game] = Game.objects.filter(
        opening_id=opening_id,
        move_count_ply__isnull=False,
    )
    agg = qs.aggregate(
        game_count=Count("id"),
        white_wins=Count("id", filter=Q(result="1-0")),
        draws=Count("id", filter=Q(result="1/2-1/2")),
        black_wins=Count("id", filter=Q(result="0-1")),
        reaches_endgame=Count("id", filter=Q(endgame_move_ply__isnull=False)),
        avg_white=Avg(
            ExpressionWrapper(
                (F("move_count_ply") + 1) / 2.0,
                output_field=FloatField(),
            ),
            filter=Q(result="1-0"),
        ),
        avg_black=Avg(
            ExpressionWrapper(
                F("move_count_ply") / 2.0,
                output_field=FloatField(),
            ),
            filter=Q(result="0-1"),
        ),
        avg_endgame_ply=Avg(
            ExpressionWrapper(
                (F("endgame_move_ply") + 1) / 2.0,
                output_field=FloatField(),
            ),
            filter=Q(endgame_move_ply__isnull=False),
        ),
    )

    if agg["game_count"] == 0:
        return None

    avg_white = agg["avg_white"]
    avg_black = agg["avg_black"]
    game_count = agg["game_count"]
    reaches_endgame = agg["reaches_endgame"]
    pct_reaches_endgame = (
        round(100.0 * reaches_endgame / game_count, 2) if game_count else 0.0
    )
    avg_endgame = agg["avg_endgame_ply"]

    return {
        "opening_id": opening.id,
        "eco_code": opening.eco_code,
        "name": opening.name,
        "moves": opening.moves,
        "game_count": game_count,
        "white_wins": agg["white_wins"],
        "draws": agg["draws"],
        "black_wins": agg["black_wins"],
        "avg_move_number_white_wins": (
            round(avg_white, 2) if avg_white is not None else None
        ),
        "avg_move_number_black_wins": (
            round(avg_black, 2) if avg_black is not None else None
        ),
        "games_reaching_endgame": reaches_endgame,
        "pct_reaches_endgame": pct_reaches_endgame,
        "avg_move_number_endgame": (
            round(avg_endgame, 2) if avg_endgame is not None else None
        ),
    }
