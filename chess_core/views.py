"""Views for the HTMX explorer UI."""

import re
from datetime import date
from urllib.parse import urlencode

from django.shortcuts import get_object_or_404, render
from pydantic import ValidationError

from chess_core.api.schemas import OpeningStatsFilterSchema
from chess_core.models import Opening
from chess_core.services.latest_game import get_latest_game_for_opening
from chess_core.services.opening_stats import (
    ALLOWED_SORT_FIELDS,
    OpeningStatsFilterParams,
    OpeningStatsService,
)
from chess_core.services.win_rate_over_time import (
    WinRateOverTimeFilterParams,
    get_win_rate_over_time,
)

RESULT_TOKENS = frozenset({"1-0", "0-1", "1/2-1/2", "*"})


def _parse_moves_to_table(moves_str: str) -> list[dict[str, str | int]]:
    """Parse PGN move text into rows for a (number, white, black) table.

    Drops result tokens (1-0, 0-1, 1/2-1/2, *) and supports standard
    "1. e4 e5 2. Nf3 Nc6" style notation.
    """
    if not moves_str or not moves_str.strip():
        return []
    text = moves_str.strip()
    for res in RESULT_TOKENS:
        if text.endswith(res):
            text = text[: -len(res)].strip()
            break
    segments = re.split(r"\s*\d+\.\s*", text)
    rows: list[dict[str, str | int]] = []
    for seg in segments:
        seg = seg.strip()
        if not seg:
            continue
        tokens = [t for t in seg.split() if t not in RESULT_TOKENS]
        if not tokens:
            continue
        move_num = len(rows) + 1
        white = tokens[0]
        black = tokens[1] if len(tokens) > 1 else ""
        rows.append({"num": move_num, "white": white, "black": black})
    return rows


def _get_params_from_request(request):
    """Build filter params and form data from request.GET.

    Returns:
        Tuple of (filter_params, form_data, validation_error).
        On success: (OpeningStatsFilterParams, request.GET.dict(), None).
        On ValidationError: (default params, raw GET dict, ValidationError).
    """
    raw = request.GET.dict()
    data = {k: v for k, v in raw.items() if v != ""}
    if "threshold" not in data:
        data["threshold"] = 10
    if "opening_threshold" not in data:
        data["opening_threshold"] = 3
    try:
        schema = OpeningStatsFilterSchema(**data)
        params = OpeningStatsFilterParams(**schema.model_dump())
        return params, raw, None
    except ValidationError as e:
        return OpeningStatsFilterParams(), raw, e


def _get_chart_params_from_request(request) -> WinRateOverTimeFilterParams:
    """Build win-rate-over-time filter params from request.GET."""
    get_dict = request.GET.dict()
    period = get_dict.get("chart_period") or "week"
    if period not in ("week", "month", "year"):
        period = "week"
    date_from = None
    if get_dict.get("date_from"):
        try:
            date_from = date.fromisoformat(get_dict["date_from"])
        except (ValueError, TypeError):
            pass
    date_to = None
    if get_dict.get("date_to"):
        try:
            date_to = date.fromisoformat(get_dict["date_to"])
        except (ValueError, TypeError):
            pass
    threshold_val = get_dict.get("threshold")
    min_games = 1
    if threshold_val is not None:
        try:
            min_games = max(1, int(threshold_val))
        except (ValueError, TypeError):
            pass
    return WinRateOverTimeFilterParams(
        period=period,
        date_from=date_from,
        date_to=date_to,
        eco_code=get_dict.get("eco_code") or None,
        opening_name=get_dict.get("opening_name") or None,
        min_games=min_games,
    )


def _build_sort_urls(get_dict: dict) -> tuple[dict, dict, str, str]:
    """Build sort query strings and per-column link info for the table headers.

    Sort links reset to page=1 so changing sort shows the first page of the
    new order.

    Returns:
        Tuple of (sort_urls, column_links, current_sort_by, current_order).
        column_links keys: eco_code, name, moves, game_count, white_wins, draws,
        black_wins, avg_moves; each value is {"url": "...", "indicator": "↑"|"↓"|""}.
    """
    sort_urls = {}
    for sort_by in ALLOWED_SORT_FIELDS:
        for order in ("asc", "desc"):
            key = f"{sort_by}_{order}"
            q = {**get_dict, "sort_by": sort_by, "order": order, "page": "1"}
            sort_urls[key] = "?" + urlencode(q)
    current_sort_by = get_dict.get("sort_by") or "game_count"
    current_order = get_dict.get("order") or "desc"
    if current_sort_by not in ALLOWED_SORT_FIELDS:
        current_sort_by = "game_count"
    if current_order not in ("asc", "desc"):
        current_order = "desc"

    column_links = {}
    for field in ALLOWED_SORT_FIELDS:
        if current_sort_by == field:
            next_order = "asc" if current_order == "desc" else "desc"
            column_links[field] = {
                "url": sort_urls[f"{field}_{next_order}"],
                "indicator": "↓" if current_order == "desc" else "↑",
            }
        else:
            column_links[field] = {
                "url": sort_urls[f"{field}_desc"],
                "indicator": "",
            }

    # Results column: desc = white_pct desc (white perspective), asc = black_pct desc (black perspective)
    if current_sort_by == "white_pct" and current_order == "desc":
        column_links["results"] = {
            "url": sort_urls["black_pct_desc"],
            "indicator": "↓",
            "label": "Results",
        }
    elif current_sort_by == "black_pct" and current_order == "desc":
        column_links["results"] = {
            "url": sort_urls["white_pct_desc"],
            "indicator": "↑",
            "label": "Results",
        }
    else:
        column_links["results"] = {
            "url": sort_urls["white_pct_desc"],
            "indicator": "",
            "label": "Results",
        }

    return sort_urls, column_links, current_sort_by, current_order


def _build_pagination(get_dict: dict, total_count: int) -> dict:
    """Build pagination context for the partial and full page."""
    page = max(1, int(get_dict.get("page") or 1))
    page_size = max(1, min(100, int(get_dict.get("page_size") or 10)))
    total_pages = max(1, (total_count + page_size - 1) // page_size)
    page = min(page, total_pages)
    prev_url = None
    if page > 1:
        q = {**get_dict, "page": str(page - 1)}
        prev_url = "?" + urlencode(q)
    next_url = None
    if page < total_pages:
        q = {**get_dict, "page": str(page + 1)}
        next_url = "?" + urlencode(q)
    return {
        "page": page,
        "page_size": page_size,
        "total_count": total_count,
        "total_pages": total_pages,
        "prev_url": prev_url,
        "next_url": next_url,
    }


def explore_openings(request):
    """Serve the opening explorer: full page or HTMX partial.

    Uses OpeningStatsService with filters from GET. On validation error,
    falls back to default params and shows an error message on the full page.
    """
    filter_params, form_data, validation_error = _get_params_from_request(request)
    service = OpeningStatsService()
    results, total_count = service.get_stats(filter_params)

    stats = [
        {
            "opening_id": r["opening_id"],
            "eco_code": r["opening__eco_code"],
            "name": r["opening__name"],
            "moves": r["opening__moves"],
            "game_count": r["game_count"],
            "white_wins": r["white_wins"],
            "draws": r["draws"],
            "black_wins": r["black_wins"],
            "white_pct": r["white_pct"],
            "draw_pct": r["draw_pct"],
            "black_pct": r["black_pct"],
            "avg_moves": (
                round(r["avg_moves"], 2) if r["avg_moves"] is not None else None
            ),
        }
        for r in results
    ]
    total = total_count
    get_dict = request.GET.dict()
    sort_urls, column_links, current_sort_by, current_order = _build_sort_urls(get_dict)
    pagination = _build_pagination(get_dict, total_count)
    chart_params = _get_chart_params_from_request(request)
    chart_items = get_win_rate_over_time(chart_params)
    partial_ctx = {
        "stats": stats,
        "total": total,
        "sort_urls": sort_urls,
        "column_links": column_links,
        "current_sort_by": current_sort_by,
        "current_order": current_order,
        "pagination": pagination,
        "chart_items": chart_items,
    }

    if request.headers.get("HX-Request"):
        return render(
            request,
            "partials/explore_results.html",
            partial_ctx,
        )
    error_message = None
    if validation_error is not None:
        errs = validation_error.errors()
        error_message = errs[0]["msg"] if errs else "Invalid filters."

    return render(
        request,
        "explore.html",
        {
            "stats": stats,
            "total": total,
            "form_data": form_data,
            "validation_error_message": error_message,
            "sort_urls": sort_urls,
            "column_links": column_links,
            "current_sort_by": current_sort_by,
            "current_order": current_order,
            "pagination": pagination,
            "chart_items": chart_items,
        },
    )


def latest_game_for_opening(request, opening_id: int):
    """Serve the latest game for an opening: full page or HTMX partial.

    Returns 404 if the opening does not exist. If the opening has no games,
    renders a message instead of 404.
    """
    opening = get_object_or_404(Opening, pk=opening_id)
    game = get_latest_game_for_opening(opening_id)
    moves_table = _parse_moves_to_table(game.moves) if game else []
    context = {"opening": opening, "game": game, "moves_table": moves_table}
    if request.headers.get("HX-Request"):
        return render(
            request,
            "partials/latest_game.html",
            context,
        )
    return render(
        request,
        "latest_game.html",
        context,
    )
