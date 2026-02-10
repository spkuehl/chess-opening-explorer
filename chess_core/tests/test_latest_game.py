"""Tests for latest game per opening: service, API, and HTMX view."""

from datetime import date

import pytest
from django.test import Client

from chess_core.services.latest_game import get_latest_game_for_opening
from chess_core.tests.factories import GameFactory, OpeningFactory


@pytest.mark.django_db
class TestGetLatestGameForOpening:
    """Tests for get_latest_game_for_opening service."""

    def test_returns_none_when_no_games(self, db: None) -> None:
        """Opening with no games returns None."""
        opening = OpeningFactory()
        assert get_latest_game_for_opening(opening.id) is None

    def test_returns_only_game(self, db: None) -> None:
        """Opening with one game returns that game."""
        opening = OpeningFactory()
        game = GameFactory(opening=opening, white_player="A", black_player="B")
        result = get_latest_game_for_opening(opening.id)
        assert result is not None
        assert result.id == game.id
        assert result.white_player == "A"

    def test_returns_most_recent_by_date_then_id(self, db: None) -> None:
        """Multiple games: returns latest by date desc, then id desc."""
        opening = OpeningFactory()
        GameFactory(
            opening=opening,
            date=date(2025, 1, 1),
            white_player="Old",
            black_player="X",
        )
        GameFactory(
            opening=opening,
            date=date(2026, 1, 1),
            white_player="Mid",
            black_player="X",
        )
        latest = GameFactory(
            opening=opening,
            date=date(2026, 6, 1),
            white_player="Latest",
            black_player="X",
        )
        result = get_latest_game_for_opening(opening.id)
        assert result is not None
        assert result.id == latest.id
        assert result.white_player == "Latest"

    def test_null_date_sorts_last(self, db: None) -> None:
        """Game with date is preferred over game with null date."""
        opening = OpeningFactory()
        GameFactory(
            opening=opening,
            date=None,
            white_player="NoDate",
            black_player="X",
        )
        GameFactory(
            opening=opening,
            date=date(2026, 1, 1),
            white_player="WithDate",
            black_player="X",
        )
        result = get_latest_game_for_opening(opening.id)
        assert result is not None
        assert result.white_player == "WithDate"


@pytest.mark.django_db
class TestLatestGameAPI:
    """Tests for GET /api/v1/openings/{opening_id}/latest-game/."""

    @pytest.fixture
    def api_client(self) -> Client:
        return Client()

    def test_200_returns_latest_game_schema(
        self, api_client: Client, db: None
    ) -> None:
        """Valid opening with game returns 200 and LatestGameSchema fields."""
        opening = OpeningFactory(eco_code="B20", name="Sicilian")
        GameFactory(
            opening=opening,
            white_player="White",
            black_player="Black",
            result="1-0",
            event="Test Event",
            moves="1. e4 c5",
        )
        response = api_client.get(f"/api/v1/openings/{opening.id}/latest-game/")
        assert response.status_code == 200
        data = response.json()
        assert data["white_player"] == "White"
        assert data["black_player"] == "Black"
        assert data["result"] == "1-0"
        assert "id" in data
        assert "source_id" in data
        assert "date" in data
        assert "moves" in data

    def test_404_when_opening_has_no_games(
        self, api_client: Client, db: None
    ) -> None:
        """Opening with no games returns 404."""
        opening = OpeningFactory()
        response = api_client.get(f"/api/v1/openings/{opening.id}/latest-game/")
        assert response.status_code == 404

    def test_404_when_opening_id_invalid(
        self, api_client: Client, db: None
    ) -> None:
        """Invalid opening_id returns 404."""
        response = api_client.get("/api/v1/openings/99999/latest-game/")
        assert response.status_code == 404


@pytest.mark.django_db
class TestLatestGameView:
    """Tests for HTMX latest-game view."""

    @pytest.fixture
    def client(self) -> Client:
        return Client()

    def test_htmx_returns_partial_with_game(
        self, client: Client, db: None
    ) -> None:
        """HX-Request returns partial containing game info."""
        opening = OpeningFactory(eco_code="B33", name="Sicilian")
        GameFactory(
            opening=opening,
            white_player="Alice",
            black_player="Bob",
            result="1/2-1/2",
        )
        response = client.get(
            f"/openings/{opening.id}/latest-game/",
            HTTP_HX_REQUEST="true",
        )
        assert response.status_code == 200
        content = response.content.decode("utf-8")
        assert "Alice" in content
        assert "Bob" in content
        assert "1/2-1/2" in content
        assert "<html" not in content.lower()

    def test_htmx_returns_partial_no_games(
        self, client: Client, db: None
    ) -> None:
        """HX-Request with opening that has no games returns partial message."""
        opening = OpeningFactory()
        response = client.get(
            f"/openings/{opening.id}/latest-game/",
            HTTP_HX_REQUEST="true",
        )
        assert response.status_code == 200
        assert b"No games for this opening" in response.content

    def test_full_page_returns_html_with_game(
        self, client: Client, db: None
    ) -> None:
        """Without HX-Request returns full page with game."""
        opening = OpeningFactory(name="French Defense")
        GameFactory(opening=opening, white_player="W", black_player="B")
        response = client.get(f"/openings/{opening.id}/latest-game/")
        assert response.status_code == 200
        content = response.content.decode("utf-8")
        assert "Latest game" in content
        assert "French Defense" in content
        assert "W" in content and "B" in content

    def test_404_invalid_opening_id(self, client: Client, db: None) -> None:
        """Invalid opening_id returns 404."""
        response = client.get("/openings/99999/latest-game/")
        assert response.status_code == 404
