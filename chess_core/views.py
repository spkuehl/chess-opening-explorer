"""Views for the HTMX explorer UI."""

from django.shortcuts import render
from pydantic import ValidationError

from chess_core.api.schemas import OpeningStatsFilterSchema
from chess_core.services.opening_stats import (
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

    if request.headers.get("HX-Request"):
        return render(
            request,
            "partials/opening_stats_table.html",
            {"stats": stats, "total": total},
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
        },
    )
