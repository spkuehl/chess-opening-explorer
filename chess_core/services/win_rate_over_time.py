"""Service for win rate over time (stacked line chart data)."""

from dataclasses import dataclass
from datetime import date
from typing import Literal

from django.db.models import Count, Q, QuerySet
from django.db.models.functions import TruncMonth, TruncWeek, TruncYear

from chess_core.models import Game

PeriodType = Literal["week", "month", "year"]

MAX_POINTS = {"week": 520, "month": 120, "year": 20}


@dataclass
class WinRateOverTimeFilterParams:
    """Filter parameters for win-rate-over-time queries.

    All fields optional. period defaults to "week".
    """

    period: PeriodType = "week"
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


def _format_period(period_date: date, period_type: PeriodType) -> tuple[str, str]:
    """Return (period, period_label) for a truncated date.

    period: stable id (ISO week, YYYY-MM, or YYYY). period_label: human-readable;
    for week period this is the first day of the week (e.g. "Mon, 03 Feb").
    """
    if period_type == "week":
        iso = period_date.isocalendar()
        period = f"{iso[0]}-W{iso[1]:02d}"
        period_label = period_date.strftime("%d %b")
    elif period_type == "month":
        period = period_date.strftime("%Y-%m")
        period_label = period
    else:
        period = period_date.strftime("%Y")
        period_label = period
    return period, period_label


def get_win_rate_over_time(
    filters: WinRateOverTimeFilterParams,
) -> list[dict]:
    """Return time-series points of white/draw/black win percentages by period.

    Uses Game.date for the X axis; buckets by week, month, or year per
    filters.period. Excludes games with null date.
    """
    qs = Game.objects.filter(date__isnull=False)
    qs = _apply_filters(qs, filters)

    if filters.period == "week":
        trunc = TruncWeek("date")
    elif filters.period == "month":
        trunc = TruncMonth("date")
    else:
        trunc = TruncYear("date")

    qs = (
        qs.annotate(period_date=trunc)
        .values("period_date")
        .annotate(
            game_count=Count("id"),
            white_wins=Count("id", filter=Q(result="1-0")),
            draws=Count("id", filter=Q(result="1/2-1/2")),
            black_wins=Count("id", filter=Q(result="0-1")),
        )
    )
    if filters.min_games > 0:
        qs = qs.filter(game_count__gte=filters.min_games)
    qs = qs.order_by("period_date")

    cap = MAX_POINTS.get(filters.period)
    if cap is not None:
        qs = qs[:cap]

    items: list[dict] = []
    for row in qs:
        period_date = row["period_date"]
        if period_date is None:
            continue
        if hasattr(period_date, "date"):
            period_date = period_date.date()
        period, period_label = _format_period(period_date, filters.period)
        n = row["game_count"]
        scale = 100.0 / n if n else 0
        items.append(
            {
                "period": period,
                "period_label": period_label,
                "white_pct": round(row["white_wins"] * scale, 2),
                "draw_pct": round(row["draws"] * scale, 2),
                "black_pct": round(row["black_wins"] * scale, 2),
                "game_count": n,
            }
        )
    return items


def _apply_filters(qs: QuerySet, filters: WinRateOverTimeFilterParams) -> QuerySet:
    """Apply player, opening, date, and ELO filters."""
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
    if filters.eco_code:
        qs = qs.filter(opening__eco_code=filters.eco_code)
    if filters.opening_id is not None:
        qs = qs.filter(opening_id=filters.opening_id)
    if filters.opening_name:
        qs = qs.filter(opening__name__icontains=filters.opening_name)
    if filters.opening_threshold is not None:
        qs = qs.filter(opening__ply_count__gte=filters.opening_threshold)
    if filters.date_from:
        qs = qs.filter(date__gte=filters.date_from)
    if filters.date_to:
        qs = qs.filter(date__lte=filters.date_to)
    if filters.white_elo_min is not None:
        qs = qs.filter(white_elo__gte=filters.white_elo_min)
    if filters.white_elo_max is not None:
        qs = qs.filter(white_elo__lte=filters.white_elo_max)
    if filters.black_elo_min is not None:
        qs = qs.filter(black_elo__gte=filters.black_elo_min)
    if filters.black_elo_max is not None:
        qs = qs.filter(black_elo__lte=filters.black_elo_max)
    return qs
