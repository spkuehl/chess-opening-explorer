"""Service for fetching the most recent game per opening."""

from django.db.models import F

from chess_core.models import Game


def get_latest_game_for_opening(opening_id: int) -> Game | None:
    """Return the most recent game for the given opening, or None.

    Orders by game date descending (nulls last), then by id descending
    for tiebreak.

    Args:
        opening_id: Primary key of the Opening.

    Returns:
        The most recent Game with this opening, or None if there are no games.
    """
    return (
        Game.objects.filter(opening_id=opening_id)
        .order_by(F("date").desc(nulls_last=True), "-id")
        .select_related("opening")
        .first()
    )
