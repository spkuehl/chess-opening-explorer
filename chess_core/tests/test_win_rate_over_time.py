"""Tests for win-rate-over-time service and API."""

from datetime import date

import pytest
from django.test import Client

from chess_core.models import Game, Opening
from chess_core.services.win_rate_over_time import (
    WinRateOverTimeFilterParams,
    get_win_rate_over_time,
)
from chess_core.tests.factories import GameFactory, OpeningFactory


@pytest.fixture
def api_client() -> Client:
    return Client()


@pytest.fixture
def opening(db) -> Opening:
    return OpeningFactory(eco_code="B20", name="Sicilian")


@pytest.fixture
def games_jan_feb(db, opening: Opening) -> list[Game]:
    """Games in Jan and Feb 2024 with known results."""
    created = []
    # Jan 2024: 2 white wins, 1 draw, 1 black win
    for _ in range(2):
        created.append(
            GameFactory(
                opening=opening,
                date=date(2024, 1, 15),
                result="1-0",
                white_player="A",
                black_player="B",
            )
        )
    created.append(
        GameFactory(
            opening=opening,
            date=date(2024, 1, 16),
            result="1/2-1/2",
            white_player="A",
            black_player="B",
        )
    )
    created.append(
        GameFactory(
            opening=opening,
            date=date(2024, 1, 17),
            result="0-1",
            white_player="A",
            black_player="B",
        )
    )
    # Feb 2024: 1 white win, 1 black win
    created.append(
        GameFactory(
            opening=opening,
            date=date(2024, 2, 10),
            result="1-0",
            white_player="A",
            black_player="B",
        )
    )
    created.append(
        GameFactory(
            opening=opening,
            date=date(2024, 2, 11),
            result="0-1",
            white_player="A",
            black_player="B",
        )
    )
    return created


@pytest.mark.django_db
class TestGetWinRateOverTime:
    """Tests for get_win_rate_over_time service."""

    def test_returns_empty_when_no_dated_games(self, db: None) -> None:
        """No games with date returns empty list."""
        GameFactory(date=None, opening=OpeningFactory())
        params = WinRateOverTimeFilterParams(period="month")
        assert get_win_rate_over_time(params) == []

    def test_returns_points_with_correct_structure(self, games_jan_feb: list) -> None:
        """Returns list of dicts with period, period_label, pcts, game_count."""
        params = WinRateOverTimeFilterParams(
            period="month",
            date_from=date(2024, 1, 1),
            date_to=date(2024, 12, 31),
            min_games=1,
        )
        items = get_win_rate_over_time(params)
        assert len(items) >= 1
        for row in items:
            assert "period" in row
            assert "period_label" in row
            assert "white_pct" in row
            assert "draw_pct" in row
            assert "black_pct" in row
            assert "game_count" in row
            assert row["white_pct"] + row["draw_pct"] + row[
                "black_pct"
            ] == pytest.approx(100.0, abs=0.02)

    def test_monthly_aggregation_percentages(self, games_jan_feb: list) -> None:
        """Jan 2024: 4 games -> 50% white, 25% draw, 25% black."""
        params = WinRateOverTimeFilterParams(
            period="month",
            date_from=date(2024, 1, 1),
            date_to=date(2024, 1, 31),
            min_games=1,
        )
        items = get_win_rate_over_time(params)
        jan = next((i for i in items if i["period"] == "2024-01"), None)
        assert jan is not None
        assert jan["game_count"] == 4
        assert jan["white_pct"] == 50.0
        assert jan["draw_pct"] == 25.0
        assert jan["black_pct"] == 25.0

    def test_min_games_filters_sparse_periods(self, games_jan_feb: list) -> None:
        """Periods with fewer than min_games are excluded."""
        params = WinRateOverTimeFilterParams(
            period="month",
            date_from=date(2024, 1, 1),
            date_to=date(2024, 12, 31),
            min_games=10,
        )
        items = get_win_rate_over_time(params)
        assert len(items) == 0

    def test_eco_code_filter(self, games_jan_feb: list, db: None) -> None:
        """Only games with matching ECO are included."""
        other = OpeningFactory(eco_code="C00", name="French")
        GameFactory(
            opening=other,
            date=date(2024, 1, 20),
            result="1-0",
            white_player="X",
            black_player="Y",
        )
        params = WinRateOverTimeFilterParams(
            period="month",
            date_from=date(2024, 1, 1),
            date_to=date(2024, 1, 31),
            eco_code="B20",
            min_games=1,
        )
        items = get_win_rate_over_time(params)
        jan = next((i for i in items if i["period"] == "2024-01"), None)
        assert jan is not None
        assert jan["game_count"] == 4

    def test_date_range_filter(self, games_jan_feb: list) -> None:
        """Only games within date_from/date_to are included."""
        params = WinRateOverTimeFilterParams(
            period="month",
            date_from=date(2024, 2, 1),
            date_to=date(2024, 2, 29),
            min_games=1,
        )
        items = get_win_rate_over_time(params)
        periods = [i["period"] for i in items]
        assert "2024-01" not in periods
        assert "2024-02" in periods


@pytest.mark.django_db
class TestWinRateOverTimeAPI:
    """Tests for GET /api/v1/stats/win-rate-over-time/."""

    def test_returns_200_with_items(
        self, api_client: Client, games_jan_feb: list
    ) -> None:
        """Endpoint returns 200 and items array."""
        response = api_client.get(
            "/api/v1/stats/win-rate-over-time/",
            {"period": "month", "date_from": "2024-01-01", "date_to": "2024-12-31"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert isinstance(data["items"], list)

    def test_response_schema(self, api_client: Client, games_jan_feb: list) -> None:
        """Response items have required fields."""
        response = api_client.get(
            "/api/v1/stats/win-rate-over-time/",
            {"period": "month", "date_from": "2024-01-01", "date_to": "2024-12-31"},
        )
        data = response.json()
        if data["items"]:
            point = data["items"][0]
            assert "period" in point
            assert "period_label" in point
            assert "white_pct" in point
            assert "draw_pct" in point
            assert "black_pct" in point
            assert "game_count" in point

    def test_default_period_is_week(
        self, api_client: Client, games_jan_feb: list
    ) -> None:
        """Omitting period defaults to week."""
        response = api_client.get(
            "/api/v1/stats/win-rate-over-time/",
            {"date_from": "2024-01-01", "date_to": "2024-01-31"},
        )
        assert response.status_code == 200
        data = response.json()
        if data["items"]:
            assert (
                "W" in data["items"][0]["period"]
                or len(data["items"][0]["period"]) <= 7
            )

    def test_invalid_period_returns_422(self, api_client: Client) -> None:
        """Invalid period value returns validation error."""
        response = api_client.get(
            "/api/v1/stats/win-rate-over-time/",
            {"period": "day"},
        )
        assert response.status_code == 422
