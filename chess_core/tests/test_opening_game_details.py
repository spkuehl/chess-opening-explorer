"""Tests for opening game details service, API, and view."""

import pytest
from django.test import Client

from chess_core.services.opening_game_details import get_opening_game_details
from chess_core.tests.factories import GameFactory, OpeningFactory


@pytest.mark.django_db
class TestGetOpeningGameDetails:
    """Tests for get_opening_game_details service."""

    def test_returns_none_when_opening_does_not_exist(self) -> None:
        """Non-existent opening_id returns None."""
        assert get_opening_game_details(99999) is None

    def test_returns_none_when_opening_has_no_games(self) -> None:
        """Opening with no games returns None."""
        opening = OpeningFactory()
        assert get_opening_game_details(opening.id) is None

    def test_returns_none_when_all_games_have_null_move_count_ply(
        self, db: None
    ) -> None:
        """Opening with only games that have null move_count_ply returns None."""
        opening = OpeningFactory()
        GameFactory(opening=opening, result="1-0", move_count_ply=None)
        assert get_opening_game_details(opening.id) is None

    def test_only_white_wins_correct_avg(self, db: None) -> None:
        """Opening with only white wins: correct avg move number, black avg None."""
        opening = OpeningFactory(eco_code="B20", name="Sicilian")
        # ply 39 -> full move (39+1)/2 = 20; ply 41 -> 21. Avg = 20.5
        GameFactory(opening=opening, result="1-0", move_count_ply=39)
        GameFactory(opening=opening, result="1-0", move_count_ply=41)
        details = get_opening_game_details(opening.id)
        assert details is not None
        assert details["game_count"] == 2
        assert details["white_wins"] == 2
        assert details["black_wins"] == 0
        assert details["draws"] == 0
        assert details["avg_move_number_white_wins"] == 20.5
        assert details["avg_move_number_black_wins"] is None

    def test_only_black_wins_correct_avg(self, db: None) -> None:
        """Opening with only black wins: correct avg move number, white avg None."""
        opening = OpeningFactory(eco_code="C00", name="French")
        # ply 40 -> full move 40/2 = 20; ply 42 -> 21. Avg = 20.5
        GameFactory(opening=opening, result="0-1", move_count_ply=40)
        GameFactory(opening=opening, result="0-1", move_count_ply=42)
        details = get_opening_game_details(opening.id)
        assert details is not None
        assert details["avg_move_number_black_wins"] == 20.5
        assert details["avg_move_number_white_wins"] is None

    def test_mixed_results_and_null_ply_excluded(self, db: None) -> None:
        """Games with null move_count_ply are excluded; averages over rest."""
        opening = OpeningFactory(eco_code="A00", name="Test")
        GameFactory(opening=opening, result="1-0", move_count_ply=41)  # full 21
        GameFactory(opening=opening, result="1-0", move_count_ply=None)  # excluded
        GameFactory(opening=opening, result="0-1", move_count_ply=36)  # full 18
        GameFactory(opening=opening, result="0-1", move_count_ply=None)  # excluded
        details = get_opening_game_details(opening.id)
        assert details is not None
        assert details["game_count"] == 2
        assert details["white_wins"] == 1
        assert details["black_wins"] == 1
        assert details["avg_move_number_white_wins"] == 21.0
        assert details["avg_move_number_black_wins"] == 18.0

    def test_opening_fields_present(self, db: None) -> None:
        """Returned dict includes opening_id, eco_code, name, moves."""
        opening = OpeningFactory(
            eco_code="B33",
            name="Sicilian: Dragon",
            moves="1. e4 c5 2. Nf3 d6 3. d4 cxd4 4. Nxd4 Nf6 5. Nc3 g6",
        )
        GameFactory(opening=opening, result="1-0", move_count_ply=40)
        details = get_opening_game_details(opening.id)
        assert details is not None
        assert details["opening_id"] == opening.id
        assert details["eco_code"] == "B33"
        assert details["name"] == "Sicilian: Dragon"
        assert details["moves"] == "1. e4 c5 2. Nf3 d6 3. d4 cxd4 4. Nxd4 Nf6 5. Nc3 g6"

    def test_endgame_pct_and_avg_move_number(self, db: None) -> None:
        """pct_reaches_endgame and avg_move_number_endgame when some games have endgame."""
        opening = OpeningFactory(eco_code="A00", name="Test")
        # 2 games reach endgame at ply 41 and 43 -> full moves 21, 22. Avg = 21.5
        GameFactory(
            opening=opening,
            result="1-0",
            move_count_ply=50,
            endgame_move_ply=41,
        )
        GameFactory(
            opening=opening,
            result="0-1",
            move_count_ply=48,
            endgame_move_ply=43,
        )
        # 1 game never reaches endgame
        GameFactory(
            opening=opening,
            result="1/2-1/2",
            move_count_ply=30,
            endgame_move_ply=None,
        )
        details = get_opening_game_details(opening.id)
        assert details is not None
        assert details["game_count"] == 3
        assert details["games_reaching_endgame"] == 2
        assert details["pct_reaches_endgame"] == round(100.0 * 2 / 3, 2)
        assert details["avg_move_number_endgame"] == 21.5


@pytest.mark.django_db
class TestOpeningGameDetailsAPI:
    """Tests for GET /api/v1/openings/{opening_id}/game-details/."""

    @pytest.fixture
    def api_client(self) -> Client:
        return Client()

    def test_200_with_correct_schema(
        self, api_client: Client, db: None
    ) -> None:
        """Returns 200 and schema with opening and avg move numbers."""
        opening = OpeningFactory(eco_code="B20", name="Sicilian")
        GameFactory(opening=opening, result="1-0", move_count_ply=41)
        GameFactory(opening=opening, result="0-1", move_count_ply=40)
        response = api_client.get(f"/api/v1/openings/{opening.id}/game-details/")
        assert response.status_code == 200
        data = response.json()
        assert data["opening_id"] == opening.id
        assert data["eco_code"] == "B20"
        assert data["name"] == "Sicilian"
        assert data["game_count"] == 2
        assert data["white_wins"] == 1
        assert data["black_wins"] == 1
        assert data["avg_move_number_white_wins"] == 21.0
        assert data["avg_move_number_black_wins"] == 20.0
        assert data["games_reaching_endgame"] >= 0
        assert "pct_reaches_endgame" in data
        assert "avg_move_number_endgame" in data

    def test_404_when_opening_has_no_games(
        self, api_client: Client, db: None
    ) -> None:
        """Opening with no games returns 404."""
        opening = OpeningFactory()
        response = api_client.get(f"/api/v1/openings/{opening.id}/game-details/")
        assert response.status_code == 404

    def test_404_when_opening_id_invalid(
        self, api_client: Client, db: None
    ) -> None:
        """Invalid opening_id returns 404."""
        response = api_client.get("/api/v1/openings/99999/game-details/")
        assert response.status_code == 404


@pytest.mark.django_db
class TestOpeningGameDetailsView:
    """Smoke tests for opening game details HTMX view."""

    @pytest.fixture
    def client(self) -> Client:
        return Client()

    def test_200_when_opening_has_games_htmx(
        self, client: Client, db: None
    ) -> None:
        """HTMX request with valid opening_id returns 200 and details partial."""
        opening = OpeningFactory(eco_code="B20", name="Sicilian")
        GameFactory(opening=opening, result="1-0", move_count_ply=40)
        response = client.get(
            f"/openings/{opening.id}/details/",
            HTTP_HX_REQUEST="true",
        )
        assert response.status_code == 200
        content = response.content.decode("utf-8")
        assert "Sicilian" in content
        assert "Opening game details" in content or "opening" in content.lower()
        assert "Average move number" in content

    def test_404_when_opening_id_invalid(self, client: Client, db: None) -> None:
        """Invalid opening_id returns 404."""
        response = client.get("/openings/99999/details/")
        assert response.status_code == 404

    def test_200_when_opening_exists_but_no_games_htmx(
        self, client: Client, db: None
    ) -> None:
        """HTMX request for opening with no games: 200 with no-games message."""
        opening = OpeningFactory()
        response = client.get(
            f"/openings/{opening.id}/details/",
            HTTP_HX_REQUEST="true",
        )
        assert response.status_code == 200
        assert b"No games for this opening" in response.content

    def test_404_when_not_htmx(self, client: Client, db: None) -> None:
        """Non-HTMX request to details URL returns 404 (no standalone page)."""
        opening = OpeningFactory(eco_code="B20", name="Sicilian")
        GameFactory(opening=opening, result="1-0", move_count_ply=40)
        response = client.get(f"/openings/{opening.id}/details/")
        assert response.status_code == 404
