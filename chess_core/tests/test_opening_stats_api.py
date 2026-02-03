"""Tests for Opening Stats API endpoint."""

import pytest
from django.test import Client

from chess_core.models import Game, Opening
from chess_core.tests.factories import GameFactory, OpeningFactory


@pytest.fixture
def api_client() -> Client:
    """Create a Django test client."""
    return Client()


@pytest.fixture
def opening_sicilian(db) -> Opening:
    """Create Sicilian Defense opening."""
    return OpeningFactory(
        eco_code="B20",
        name="Sicilian Defense",
    )


@pytest.fixture
def opening_french(db) -> Opening:
    """Create French Defense opening."""
    return OpeningFactory(
        eco_code="C00",
        name="French Defense",
    )


@pytest.fixture
def opening_zukertort(db) -> Opening:
    """Create Zukertort opening used for name filter tests."""
    return OpeningFactory(
        eco_code="A04",
        name="Zukertort Opening: Arctic",
    )


@pytest.fixture
def sample_games(
    db, opening_sicilian: Opening, opening_french: Opening
) -> list[Game]:
    """Create sample games for API testing."""
    games = []

    # Sicilian games: 3 white wins, 1 draw, 1 black win
    for _ in range(3):
        games.append(
            GameFactory(
                opening=opening_sicilian,
                result="1-0",
                white_player="Magnus Carlsen",
                black_player="Hikaru Nakamura",
                move_count_ply=40,
                white_elo=2800,
                black_elo=2750,
            )
        )
    games.append(
        GameFactory(
            opening=opening_sicilian,
            result="1/2-1/2",
            white_player="Fabiano Caruana",
            black_player="Ding Liren",
            move_count_ply=50,
            white_elo=2780,
            black_elo=2790,
        )
    )
    games.append(
        GameFactory(
            opening=opening_sicilian,
            result="0-1",
            white_player="Ian Nepomniachtchi",
            black_player="Magnus Carlsen",
            move_count_ply=35,
            white_elo=2760,
            black_elo=2800,
        )
    )

    # French games: 2 white wins
    for _ in range(2):
        games.append(
            GameFactory(
                opening=opening_french,
                result="1-0",
                white_player="Anish Giri",
                black_player="Wesley So",
                move_count_ply=30,
                white_elo=2760,
                black_elo=2770,
            )
        )

    return games


@pytest.mark.django_db
class TestOpeningStatsEndpoint:
    """Tests for GET /api/v1/openings/stats/ endpoint."""

    def test_returns_200_with_valid_response(
        self, api_client: Client, sample_games: list[Game]
    ):
        """Basic happy path - returns 200 with valid JSON."""
        response = api_client.get("/api/v1/openings/stats/")

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data

    def test_response_schema_matches(
        self, api_client: Client, sample_games: list[Game]
    ):
        """Verify response structure matches expected schema."""
        response = api_client.get("/api/v1/openings/stats/")

        data = response.json()
        assert len(data["items"]) == 2

        # Check first item has all required fields
        item = data["items"][0]
        assert "eco_code" in item
        assert "name" in item
        assert "moves" in item
        assert "game_count" in item
        assert "white_wins" in item
        assert "draws" in item
        assert "black_wins" in item
        assert "white_pct" in item
        assert "draw_pct" in item
        assert "black_pct" in item
        assert "avg_moves" in item

    def test_aggregation_values_correct(
        self, api_client: Client, sample_games: list[Game]
    ):
        """Verify aggregation values are calculated correctly."""
        response = api_client.get("/api/v1/openings/stats/")

        data = response.json()

        # Sicilian should be first (5 games > 2 games French)
        sicilian = data["items"][0]
        assert sicilian["eco_code"] == "B20"
        assert sicilian["game_count"] == 5
        assert sicilian["white_wins"] == 3
        assert sicilian["draws"] == 1
        assert sicilian["black_wins"] == 1
        assert sicilian["white_pct"] == 60.0
        assert sicilian["draw_pct"] == 20.0
        assert sicilian["black_pct"] == 20.0
        # Avg moves: (40+40+40+50+35) / 5 / 2 = 20.5
        assert sicilian["avg_moves"] == 20.5

    def test_empty_results_returns_empty_list(self, api_client: Client, db):
        """Edge case: no data returns empty items list."""
        response = api_client.get("/api/v1/openings/stats/")

        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0


@pytest.mark.django_db
class TestOpeningStatsFilterParams:
    """Tests for filter query parameters."""

    def test_filter_white_player(
        self, api_client: Client, sample_games: list[Game]
    ):
        """Filter by white_player query param."""
        response = api_client.get("/api/v1/openings/stats/?white_player=Carlsen")

        data = response.json()
        # Only Carlsen as white: 3 Sicilian games
        assert data["total"] == 1
        assert data["items"][0]["game_count"] == 3

    def test_filter_any_player(
        self, api_client: Client, sample_games: list[Game]
    ):
        """Filter by any_player query param (OR condition)."""
        response = api_client.get("/api/v1/openings/stats/?any_player=Carlsen")

        data = response.json()
        # Carlsen as white (3) + Carlsen as black (1) = 4 Sicilian games
        assert data["total"] == 1
        assert data["items"][0]["game_count"] == 4

    def test_filter_threshold(
        self, api_client: Client, sample_games: list[Game]
    ):
        """Filter by threshold query param."""
        response = api_client.get("/api/v1/openings/stats/?threshold=3")

        data = response.json()
        # Only Sicilian (5 games) meets threshold of 3
        assert data["total"] == 1
        assert data["items"][0]["eco_code"] == "B20"

    def test_threshold_default_value(
        self, api_client: Client, sample_games: list[Game]
    ):
        """Default threshold is 1, including all openings with games."""
        response = api_client.get("/api/v1/openings/stats/")

        data = response.json()
        # Both Sicilian and French should be included
        assert data["total"] == 2

    def test_filter_elo_range(
        self, api_client: Client, sample_games: list[Game]
    ):
        """Filter by ELO range query params."""
        # Only Magnus has 2800 ELO as white
        response = api_client.get(
            "/api/v1/openings/stats/?white_elo_min=2800&white_elo_max=2850"
        )

        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["game_count"] == 3

    def test_combined_filters(
        self, api_client: Client, sample_games: list[Game]
    ):
        """Multiple filters combine correctly."""
        response = api_client.get(
            "/api/v1/openings/stats/?white_player=Carlsen&threshold=2"
        )

        data = response.json()
        # Carlsen as white: 3 games, meets threshold of 2
        assert data["total"] == 1
        assert data["items"][0]["game_count"] == 3

    def test_filter_eco_code(
        self, api_client: Client, sample_games: list[Game]
    ):
        """Filter by ECO code returns only that opening."""
        response = api_client.get("/api/v1/openings/stats/?eco_code=B20")

        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["eco_code"] == "B20"

    def test_filter_opening_name_contains_phrase(
        self,
        api_client: Client,
        db,
        opening_zukertort: Opening,
        opening_sicilian: Opening,
    ):
        """Filter by opening_name uses case-insensitive contains match."""
        GameFactory(opening=opening_zukertort, result="1-0", move_count_ply=40)
        GameFactory(opening=opening_sicilian, result="1-0", move_count_ply=40)

        response = api_client.get(
            "/api/v1/openings/stats/?opening_name=Zukertort%20Opening:%20Arctic"
        )

        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["name"] == "Zukertort Opening: Arctic"


@pytest.mark.django_db
class TestOpeningStatsValidation:
    """Tests for input validation and error handling."""

    def test_invalid_threshold_type_returns_422(
        self, api_client: Client, db
    ):
        """Invalid threshold type returns 422 validation error."""
        response = api_client.get("/api/v1/openings/stats/?threshold=invalid")

        assert response.status_code == 422

    def test_invalid_elo_type_returns_422(self, api_client: Client, db):
        """Invalid ELO type returns 422 validation error."""
        response = api_client.get("/api/v1/openings/stats/?white_elo_min=invalid")

        assert response.status_code == 422

    def test_invalid_date_format_returns_422(self, api_client: Client, db):
        """Invalid date format returns 422 validation error."""
        response = api_client.get(
            "/api/v1/openings/stats/?date_from=not-a-date"
        )

        assert response.status_code == 422


@pytest.mark.django_db
class TestOpeningStatsDocumentation:
    """Tests for API documentation endpoints."""

    def test_swagger_docs_available(self, api_client: Client):
        """Swagger UI is available at /api/v1/docs."""
        response = api_client.get("/api/v1/docs")

        assert response.status_code == 200

    def test_openapi_schema_available(self, api_client: Client):
        """OpenAPI schema is available."""
        response = api_client.get("/api/v1/openapi.json")

        assert response.status_code == 200
        data = response.json()
        assert "openapi" in data
        assert "paths" in data
