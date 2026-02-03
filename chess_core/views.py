"""Views for the HTMX explorer UI."""

from urllib.parse import urlencode

from django.shortcuts import render
from pydantic import ValidationError

from chess_core.api.schemas import OpeningStatsFilterSchema
from chess_core.services.opening_stats import (
    ALLOWED_SORT_FIELDS,
    OpeningStatsFilterParams,
    OpeningStatsService,
)


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
        data["threshold"] = 1
    try:
        schema = OpeningStatsFilterSchema(**data)
        params = OpeningStatsFilterParams(**schema.model_dump())
        return params, raw, None
    except ValidationError as e:
        return OpeningStatsFilterParams(), raw, e


def _build_sort_urls(get_dict: dict) -> tuple[dict, dict, str, str]:
    """Build sort query strings and per-column link info for the table headers.

    Returns:
        Tuple of (sort_urls, column_links, current_sort_by, current_order).
        column_links keys: eco_code, name, moves, game_count, white_wins, draws,
        black_wins, avg_moves; each value is {"url": "...", "indicator": "↑"|"↓"|""}.
    """
    sort_urls = {}
    for sort_by in ALLOWED_SORT_FIELDS:
        for order in ("asc", "desc"):
            key = f"{sort_by}_{order}"
            q = {**get_dict, "sort_by": sort_by, "order": order}
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
    return sort_urls, column_links, current_sort_by, current_order


def explore_openings(request):
    """Serve the opening explorer: full page or HTMX partial.

    Uses OpeningStatsService with filters from GET. On validation error,
    falls back to default params and shows an error message on the full page.
    """
    filter_params, form_data, validation_error = _get_params_from_request(request)
    service = OpeningStatsService()
    results = list(service.get_stats(filter_params))

    stats = [
        {
            "eco_code": r["opening__eco_code"],
            "name": r["opening__name"],
            "moves": r["opening__moves"],
            "game_count": r["game_count"],
            "white_wins": r["white_wins"],
            "draws": r["draws"],
            "black_wins": r["black_wins"],
            "avg_moves": (
                round(r["avg_moves"], 2) if r["avg_moves"] is not None else None
            ),
        }
        for r in results
    ]
    total = len(stats)
    sort_urls, column_links, current_sort_by, current_order = _build_sort_urls(
        request.GET.dict()
    )
    partial_ctx = {
        "stats": stats,
        "total": total,
        "sort_urls": sort_urls,
        "column_links": column_links,
        "current_sort_by": current_sort_by,
        "current_order": current_order,
    }

    if request.headers.get("HX-Request"):
        return render(
            request,
            "partials/opening_stats_table.html",
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
        },
    )
