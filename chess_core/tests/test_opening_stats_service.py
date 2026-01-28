"""Tests for OpeningStatsService."""

from datetime import date

import pytest

from chess_core.models import Game, Opening
from chess_core.services.opening_stats import OpeningStatsFilterParams, OpeningStatsService
from chess_core.tests.factories import GameFactory, OpeningFactory


@pytest.fixture
def opening_sicilian(db) -> Opening:
    """Create Sicilian Defense opening."""
    return OpeningFactory(
        eco_code="B20",
        name="Sicilian Defense",
        fen="rnbqkbnr/pp1ppppp/8/2p5/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2",
    )


@pytest.fixture
def opening_french(db) -> Opening:
    """Create French Defense opening."""
    return OpeningFactory(
        eco_code="C00",
        name="French Defense",
        fen="rnbqkbnr/pppp1ppp/4p3/8/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2",
    )


@pytest.fixture
def opening_caro_kann(db) -> Opening:
    """Create Caro-Kann Defense opening."""
    return OpeningFactory(
        eco_code="B10",
        name="Caro-Kann Defense",
        fen="rnbqkbnr/pp1ppppp/2p5/8/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2",
    )


@pytest.fixture
def opening_zukertort(db) -> Opening:
    """Create Zukertort opening used for name filter tests."""
    return OpeningFactory(
        eco_code="A04",
        name="Zukertort Opening: Arctic",
        fen="rnbqkbnr/pppppppp/8/8/NP6/8/P1PPPPPP/R1BQKBNR b KQkq - 0 1",
    )


@pytest.fixture
def games_with_openings(
    db, opening_sicilian: Opening, opening_french: Opening
) -> list[Game]:
    """Create games with different openings and results."""
    games = []

    # Sicilian games: 3 white wins, 2 draws, 1 black win
    for i in range(3):
        games.append(
            GameFactory(
                opening=opening_sicilian,
                result="1-0",
                white_player="Magnus Carlsen",
                black_player="Hikaru Nakamura",
                move_count_ply=40 + i,
                white_elo=2800,
                black_elo=2750,
            )
        )
    for i in range(2):
        games.append(
            GameFactory(
                opening=opening_sicilian,
                result="1/2-1/2",
                white_player="Fabiano Caruana",
                black_player="Ding Liren",
                move_count_ply=50 + i,
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

    # French games: 2 white wins, 1 draw
    for i in range(2):
        games.append(
            GameFactory(
                opening=opening_french,
                result="1-0",
                white_player="Anish Giri",
                black_player="Wesley So",
                move_count_ply=30 + i,
                white_elo=2760,
                black_elo=2770,
            )
        )
    games.append(
        GameFactory(
            opening=opening_french,
            result="1/2-1/2",
            white_player="Levon Aronian",
            black_player="Maxime Vachier-Lagrave",
            move_count_ply=45,
            white_elo=2750,
            black_elo=2740,
        )
    )

    return games


@pytest.mark.django_db
class TestOpeningStatsServiceAggregation:
    """Tests for OpeningStatsService aggregation logic."""

    def test_aggregates_by_opening(
        self, games_with_openings: list[Game], opening_sicilian: Opening
    ):
        """Verify stats are grouped by opening."""
        service = OpeningStatsService()
        filters = OpeningStatsFilterParams()

        results = list(service.get_stats(filters))

        # Should have 2 openings (Sicilian and French)
        assert len(results) == 2

        # Find Sicilian stats
        sicilian_stats = next(
            r for r in results if r["opening__eco_code"] == "B20"
        )
        assert sicilian_stats["opening__name"] == "Sicilian Defense"

    def test_counts_results_correctly(
        self, games_with_openings: list[Game], opening_sicilian: Opening
    ):
        """Verify white_wins, draws, black_wins counts are correct."""
        service = OpeningStatsService()
        filters = OpeningStatsFilterParams()

        results = list(service.get_stats(filters))

        sicilian_stats = next(
            r for r in results if r["opening__eco_code"] == "B20"
        )

        assert sicilian_stats["game_count"] == 6
        assert sicilian_stats["white_wins"] == 3
        assert sicilian_stats["draws"] == 2
        assert sicilian_stats["black_wins"] == 1

    def test_calculates_average_moves(
        self, games_with_openings: list[Game], opening_sicilian: Opening
    ):
        """Verify avg_moves calculation is correct."""
        service = OpeningStatsService()
        filters = OpeningStatsFilterParams()

        results = list(service.get_stats(filters))

        sicilian_stats = next(
            r for r in results if r["opening__eco_code"] == "B20"
        )

        # Sicilian ply counts: 40, 41, 42, 50, 51, 35 = 259 / 6 / 2 = 21.583...
        expected_avg = (40 + 41 + 42 + 50 + 51 + 35) / 6 / 2
        assert abs(sicilian_stats["avg_moves"] - expected_avg) < 0.01

    def test_excludes_games_without_opening(self, db, opening_sicilian: Opening):
        """Games with null opening are excluded from stats."""
        # Create game with opening
        GameFactory(opening=opening_sicilian, result="1-0", move_count_ply=40)
        # Create game without opening
        GameFactory(opening=None, result="1-0", move_count_ply=40)

        service = OpeningStatsService()
        filters = OpeningStatsFilterParams()

        results = list(service.get_stats(filters))

        # Should only have 1 opening with 1 game
        assert len(results) == 1
        assert results[0]["game_count"] == 1

    def test_empty_results(self, db):
        """Returns empty when no games exist."""
        service = OpeningStatsService()
        filters = OpeningStatsFilterParams()

        results = list(service.get_stats(filters))

        assert len(results) == 0

    def test_orders_by_game_count_descending(
        self, games_with_openings: list[Game]
    ):
        """Results are ordered by game_count descending."""
        service = OpeningStatsService()
        filters = OpeningStatsFilterParams()

        results = list(service.get_stats(filters))

        # Sicilian has 6 games, French has 3
        assert results[0]["opening__eco_code"] == "B20"
        assert results[1]["opening__eco_code"] == "C00"


@pytest.mark.django_db
class TestOpeningStatsServicePlayerFilters:
    """Tests for player filtering."""

    def test_filter_white_player(self, db, opening_sicilian: Opening):
        """Filter by white_player returns correct subset."""
        GameFactory(
            opening=opening_sicilian,
            white_player="Magnus Carlsen",
            black_player="Other",
            result="1-0",
            move_count_ply=40,
        )
        GameFactory(
            opening=opening_sicilian,
            white_player="Hikaru Nakamura",
            black_player="Other",
            result="0-1",
            move_count_ply=35,
        )

        service = OpeningStatsService()
        filters = OpeningStatsFilterParams(white_player="Carlsen")

        results = list(service.get_stats(filters))

        assert len(results) == 1
        assert results[0]["game_count"] == 1
        assert results[0]["white_wins"] == 1

    def test_filter_black_player(self, db, opening_sicilian: Opening):
        """Filter by black_player returns correct subset."""
        GameFactory(
            opening=opening_sicilian,
            white_player="Other",
            black_player="Magnus Carlsen",
            result="0-1",
            move_count_ply=40,
        )
        GameFactory(
            opening=opening_sicilian,
            white_player="Other",
            black_player="Hikaru Nakamura",
            result="1-0",
            move_count_ply=35,
        )

        service = OpeningStatsService()
        filters = OpeningStatsFilterParams(black_player="Carlsen")

        results = list(service.get_stats(filters))

        assert len(results) == 1
        assert results[0]["game_count"] == 1
        assert results[0]["black_wins"] == 1

    def test_filter_any_player(self, db, opening_sicilian: Opening):
        """Filter by any_player uses OR condition for white and black."""
        GameFactory(
            opening=opening_sicilian,
            white_player="Magnus Carlsen",
            black_player="Hikaru Nakamura",
            result="1-0",
            move_count_ply=40,
        )
        GameFactory(
            opening=opening_sicilian,
            white_player="Fabiano Caruana",
            black_player="Magnus Carlsen",
            result="0-1",
            move_count_ply=35,
        )
        GameFactory(
            opening=opening_sicilian,
            white_player="Other Player",
            black_player="Another Player",
            result="1/2-1/2",
            move_count_ply=50,
        )

        service = OpeningStatsService()
        filters = OpeningStatsFilterParams(any_player="Carlsen")

        results = list(service.get_stats(filters))

        assert len(results) == 1
        assert results[0]["game_count"] == 2
        assert results[0]["white_wins"] == 1
        assert results[0]["black_wins"] == 1

    def test_any_player_takes_precedence(self, db, opening_sicilian: Opening):
        """any_player takes precedence over white_player/black_player."""
        GameFactory(
            opening=opening_sicilian,
            white_player="Magnus Carlsen",
            black_player="Hikaru Nakamura",
            result="1-0",
            move_count_ply=40,
        )

        service = OpeningStatsService()
        # Provide both any_player and white_player
        filters = OpeningStatsFilterParams(
            any_player="Nakamura",
            white_player="Carlsen",
        )

        results = list(service.get_stats(filters))

        # Should match Nakamura (any_player), not just Carlsen as white
        assert len(results) == 1
        assert results[0]["game_count"] == 1


@pytest.mark.django_db
class TestOpeningStatsServiceDateFilters:
    """Tests for date range filtering."""

    def test_filter_game_date_range(self, db, opening_sicilian: Opening):
        """Filter by game date bounds works correctly."""
        # Create game from 2024
        GameFactory(
            opening=opening_sicilian,
            date=date(2024, 6, 15),
            result="1-0",
            move_count_ply=40,
        )
        # Create game from 2023
        GameFactory(
            opening=opening_sicilian,
            date=date(2023, 3, 10),
            result="0-1",
            move_count_ply=35,
        )

        service = OpeningStatsService()

        # Filter for 2024 games only
        filters = OpeningStatsFilterParams(
            date_from=date(2024, 1, 1),
            date_to=date(2024, 12, 31),
        )

        results = list(service.get_stats(filters))

        assert len(results) == 1
        assert results[0]["game_count"] == 1
        assert results[0]["white_wins"] == 1

    def test_filter_date_upper_bound(self, db, opening_sicilian: Opening):
        """Filter with only date upper bound works correctly."""
        # Create game from 2024
        GameFactory(
            opening=opening_sicilian,
            date=date(2024, 6, 15),
            result="1-0",
            move_count_ply=40,
        )
        # Create game from 2023
        GameFactory(
            opening=opening_sicilian,
            date=date(2023, 3, 10),
            result="0-1",
            move_count_ply=35,
        )

        service = OpeningStatsService()

        # Filter for games before 2024
        filters = OpeningStatsFilterParams(
            date_to=date(2023, 12, 31),
        )

        results = list(service.get_stats(filters))

        assert len(results) == 1
        assert results[0]["game_count"] == 1
        assert results[0]["black_wins"] == 1


@pytest.mark.django_db
class TestOpeningStatsServiceEloFilters:
    """Tests for ELO range filtering."""

    def test_filter_elo_range(self, db, opening_sicilian: Opening):
        """Filter by ELO min/max bounds works correctly."""
        # High ELO game
        GameFactory(
            opening=opening_sicilian,
            result="1-0",
            white_elo=2800,
            black_elo=2750,
            move_count_ply=40,
        )
        # Lower ELO game
        GameFactory(
            opening=opening_sicilian,
            result="0-1",
            white_elo=2400,
            black_elo=2350,
            move_count_ply=35,
        )

        service = OpeningStatsService()

        # Filter for high ELO games only (white >= 2700)
        filters = OpeningStatsFilterParams(white_elo_min=2700)

        results = list(service.get_stats(filters))

        assert len(results) == 1
        assert results[0]["game_count"] == 1
        assert results[0]["white_wins"] == 1

    def test_filter_black_elo_range(self, db, opening_sicilian: Opening):
        """Filter by black ELO range works correctly."""
        GameFactory(
            opening=opening_sicilian,
            result="1-0",
            white_elo=2500,
            black_elo=2800,
            move_count_ply=40,
        )
        GameFactory(
            opening=opening_sicilian,
            result="0-1",
            white_elo=2500,
            black_elo=2400,
            move_count_ply=35,
        )

        service = OpeningStatsService()

        # Filter for high black ELO (>= 2700)
        filters = OpeningStatsFilterParams(black_elo_min=2700)

        results = list(service.get_stats(filters))

        assert len(results) == 1
        assert results[0]["game_count"] == 1
        assert results[0]["white_wins"] == 1

    def test_filter_elo_max(self, db, opening_sicilian: Opening):
        """Filter by ELO max bound works correctly."""
        GameFactory(
            opening=opening_sicilian,
            result="1-0",
            white_elo=2800,
            black_elo=2750,
            move_count_ply=40,
        )
        GameFactory(
            opening=opening_sicilian,
            result="0-1",
            white_elo=2400,
            black_elo=2350,
            move_count_ply=35,
        )

        service = OpeningStatsService()

        # Filter for lower ELO games only (white <= 2500)
        filters = OpeningStatsFilterParams(white_elo_max=2500)

        results = list(service.get_stats(filters))

        assert len(results) == 1
        assert results[0]["game_count"] == 1
        assert results[0]["black_wins"] == 1


@pytest.mark.django_db
class TestOpeningStatsServiceOpeningFilters:
    """Tests for opening-based filters."""

    def test_filter_eco_code(
        self,
        db,
        opening_sicilian: Opening,
        opening_french: Opening,
    ):
        """Filter by ECO code returns only the requested opening."""
        GameFactory(opening=opening_sicilian, result="1-0", move_count_ply=40)
        GameFactory(opening=opening_french, result="1-0", move_count_ply=35)

        service = OpeningStatsService()
        filters = OpeningStatsFilterParams(eco_code="B20")

        results = list(service.get_stats(filters))

        assert len(results) == 1
        assert results[0]["opening__eco_code"] == "B20"

    def test_filter_opening_name_contains_phrase(
        self,
        db,
        opening_zukertort: Opening,
        opening_sicilian: Opening,
    ):
        """Filter by opening_name uses case-insensitive contains match."""
        GameFactory(opening=opening_zukertort, result="1-0", move_count_ply=40)
        GameFactory(opening=opening_sicilian, result="1-0", move_count_ply=40)

        service = OpeningStatsService()
        filters = OpeningStatsFilterParams(
            opening_name="Zukertort Opening: Arctic",
        )

        results = list(service.get_stats(filters))

        assert len(results) == 1
        assert results[0]["opening__name"] == "Zukertort Opening: Arctic"


@pytest.mark.django_db
class TestOpeningStatsServiceThreshold:
    """Tests for threshold filtering."""

    def test_threshold_excludes_low_count(
        self, db, opening_sicilian: Opening, opening_french: Opening
    ):
        """Openings below threshold are excluded from results."""
        # 5 Sicilian games
        for _ in range(5):
            GameFactory(opening=opening_sicilian, result="1-0", move_count_ply=40)

        # 2 French games
        for _ in range(2):
            GameFactory(opening=opening_french, result="1-0", move_count_ply=35)

        service = OpeningStatsService()

        # Require at least 3 games
        filters = OpeningStatsFilterParams(threshold=3)

        results = list(service.get_stats(filters))

        # Only Sicilian should be included
        assert len(results) == 1
        assert results[0]["opening__eco_code"] == "B20"
        assert results[0]["game_count"] == 5

    def test_threshold_default_includes_all(
        self, db, opening_sicilian: Opening, opening_french: Opening
    ):
        """Default threshold of 1 includes all openings with at least 1 game."""
        GameFactory(opening=opening_sicilian, result="1-0", move_count_ply=40)
        GameFactory(opening=opening_french, result="1-0", move_count_ply=35)

        service = OpeningStatsService()
        filters = OpeningStatsFilterParams()  # Default threshold=1

        results = list(service.get_stats(filters))

        assert len(results) == 2

    def test_threshold_zero_includes_all(
        self, db, opening_sicilian: Opening
    ):
        """Threshold of 0 includes all openings."""
        GameFactory(opening=opening_sicilian, result="1-0", move_count_ply=40)

        service = OpeningStatsService()
        filters = OpeningStatsFilterParams(threshold=0)

        results = list(service.get_stats(filters))

        assert len(results) == 1
