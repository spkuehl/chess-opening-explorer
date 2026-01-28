"""Tests for GameRepository."""

from datetime import date

import pytest

from chess_core.models import Game
from chess_core.parsers.base import GameData
from chess_core.repositories import GameRepository

from .factories import GameFactory, OpeningFactory


def make_game_data(
    source_id: str = "test-source-id",
    event: str = "Test Event",
    site: str = "Test Site",
    game_date: date | None = None,
    round_num: str | None = "1",
    white_player: str = "White",
    black_player: str = "Black",
    result: str = "1-0",
    white_elo: int | None = 2500,
    black_elo: int | None = 2400,
    time_control: str | None = "300+0",
    termination: str | None = "Normal",
    moves: str = "1. e4 e5",
    opening_fen: str = "",
) -> GameData:
    """Helper to create GameData instances for testing."""
    return GameData(
        source_id=source_id,
        event=event,
        site=site,
        date=game_date,
        round=round_num,
        white_player=white_player,
        black_player=black_player,
        result=result,
        white_elo=white_elo,
        black_elo=black_elo,
        time_control=time_control,
        termination=termination,
        moves=moves,
        source_format="pgn",
        raw_headers={"Event": event, "White": white_player},
        opening_fen=opening_fen,
    )


@pytest.mark.django_db
class TestGameRepositoryInit:
    """Tests for GameRepository initialization."""

    def test_init_loads_opening_cache(self):
        """Repository loads opening FEN cache on init."""
        opening = OpeningFactory()
        repo = GameRepository()

        assert opening.fen in repo._opening_cache
        assert repo._opening_cache[opening.fen] == opening.id

    def test_init_empty_database(self):
        """Repository handles empty opening table."""
        repo = GameRepository()
        assert repo._opening_cache == {}

    def test_init_multiple_openings(self):
        """Repository loads all openings into cache."""
        openings = OpeningFactory.create_batch(5)
        repo = GameRepository()

        assert len(repo._opening_cache) == 5
        for opening in openings:
            assert repo._opening_cache[opening.fen] == opening.id


@pytest.mark.django_db
class TestGameRepositorySave:
    """Tests for GameRepository.save method."""

    def test_save_creates_game(self):
        """save() creates a new game."""
        repo = GameRepository()
        game_data = make_game_data(source_id="new-game")

        game = repo.save(game_data)

        assert game.pk is not None
        assert game.source_id == "new-game"
        assert game.white_player == "White"

    def test_save_updates_existing_game(self):
        """save() updates existing game with same source_id."""
        repo = GameRepository()
        game_data = make_game_data(source_id="existing-game", white_player="Original")
        repo.save(game_data)

        # Update the game
        updated_data = make_game_data(source_id="existing-game", white_player="Updated")
        game = repo.save(updated_data)

        assert Game.objects.count() == 1
        assert game.white_player == "Updated"

    def test_save_returns_game_instance(self):
        """save() returns Game model instance."""
        repo = GameRepository()
        game_data = make_game_data()

        result = repo.save(game_data)

        assert isinstance(result, Game)

    def test_save_with_opening_fen(self):
        """save() resolves opening_fen to opening_id."""
        opening = OpeningFactory()
        repo = GameRepository()
        game_data = make_game_data(opening_fen=opening.fen)

        game = repo.save(game_data)

        assert game.opening_id == opening.id

    def test_save_with_unknown_opening_fen(self):
        """save() sets opening to None if FEN not in cache."""
        repo = GameRepository()
        game_data = make_game_data(opening_fen="unknown-fen")

        game = repo.save(game_data)

        assert game.opening is None

    def test_save_with_empty_opening_fen(self):
        """save() sets opening to None if opening_fen is empty."""
        repo = GameRepository()
        game_data = make_game_data(opening_fen="")

        game = repo.save(game_data)

        assert game.opening is None

    def test_save_converts_none_round(self):
        """save() converts None round to empty string."""
        repo = GameRepository()
        game_data = make_game_data(round_num=None)

        game = repo.save(game_data)

        assert game.round == ""

    def test_save_converts_none_time_control(self):
        """save() converts None time_control to empty string."""
        repo = GameRepository()
        game_data = make_game_data(time_control=None)

        game = repo.save(game_data)

        assert game.time_control == ""

    def test_save_converts_none_termination(self):
        """save() converts None termination to empty string."""
        repo = GameRepository()
        game_data = make_game_data(termination=None)

        game = repo.save(game_data)

        assert game.termination == ""


@pytest.mark.django_db
class TestGameRepositorySaveBatch:
    """Tests for GameRepository.save_batch method."""

    def test_save_batch_empty(self):
        """save_batch() handles empty iterable."""
        repo = GameRepository()
        count = repo.save_batch([])

        assert count == 0
        assert Game.objects.count() == 0

    def test_save_batch_single_game(self):
        """save_batch() saves a single game."""
        repo = GameRepository()
        games = [make_game_data(source_id="batch-1")]

        count = repo.save_batch(games)

        assert count == 1
        assert Game.objects.count() == 1

    def test_save_batch_multiple_games(self):
        """save_batch() saves multiple games."""
        repo = GameRepository()
        games = [
            make_game_data(source_id="batch-1"),
            make_game_data(source_id="batch-2"),
            make_game_data(source_id="batch-3"),
        ]

        count = repo.save_batch(games)

        assert count == 3
        assert Game.objects.count() == 3

    def test_save_batch_returns_total_processed(self):
        """save_batch() returns total number processed."""
        repo = GameRepository()
        games = [make_game_data(source_id=f"game-{i}") for i in range(5)]

        count = repo.save_batch(games)

        assert count == 5

    def test_save_batch_smaller_than_batch_size(self):
        """save_batch() handles batch smaller than batch_size."""
        repo = GameRepository()
        games = [make_game_data(source_id=f"game-{i}") for i in range(3)]

        count = repo.save_batch(games, batch_size=100)

        assert count == 3
        assert Game.objects.count() == 3

    def test_save_batch_equals_batch_size(self):
        """save_batch() handles batch exactly equal to batch_size."""
        repo = GameRepository()
        games = [make_game_data(source_id=f"game-{i}") for i in range(5)]

        count = repo.save_batch(games, batch_size=5)

        assert count == 5
        assert Game.objects.count() == 5

    def test_save_batch_larger_than_batch_size(self):
        """save_batch() handles batch larger than batch_size."""
        repo = GameRepository()
        games = [make_game_data(source_id=f"game-{i}") for i in range(7)]

        count = repo.save_batch(games, batch_size=3)

        assert count == 7
        assert Game.objects.count() == 7

    def test_save_batch_skips_duplicates(self):
        """save_batch() skips games with duplicate source_id."""
        repo = GameRepository()
        # Create an existing game
        GameFactory(source_id="existing")

        games = [
            make_game_data(source_id="existing"),  # Duplicate
            make_game_data(source_id="new-game"),
        ]

        count = repo.save_batch(games)

        assert count == 2  # Both processed
        assert Game.objects.count() == 2  # But only 2 in DB (one existing + one new)

    def test_save_batch_with_generator(self):
        """save_batch() works with generator."""
        repo = GameRepository()

        def game_generator():
            for i in range(3):
                yield make_game_data(source_id=f"gen-{i}")

        count = repo.save_batch(game_generator())

        assert count == 3
        assert Game.objects.count() == 3

    def test_save_batch_with_openings(self):
        """save_batch() resolves opening_fen for all games."""
        opening = OpeningFactory()
        repo = GameRepository()
        games = [
            make_game_data(source_id="game-1", opening_fen=opening.fen),
            make_game_data(source_id="game-2", opening_fen=opening.fen),
        ]

        repo.save_batch(games)

        saved_games = Game.objects.all()
        assert all(g.opening_id == opening.id for g in saved_games)


@pytest.mark.django_db
class TestGameRepositoryExists:
    """Tests for GameRepository.exists method."""

    def test_exists_returns_true(self):
        """exists() returns True for existing game."""
        GameFactory(source_id="existing-game")
        repo = GameRepository()

        assert repo.exists("existing-game") is True

    def test_exists_returns_false(self):
        """exists() returns False for non-existing game."""
        repo = GameRepository()

        assert repo.exists("nonexistent") is False


@pytest.mark.django_db
class TestGameRepositoryCount:
    """Tests for GameRepository.count method."""

    def test_count_empty(self):
        """count() returns 0 for empty database."""
        repo = GameRepository()

        assert repo.count() == 0

    def test_count_with_games(self):
        """count() returns correct count."""
        GameFactory.create_batch(5)
        repo = GameRepository()

        assert repo.count() == 5


@pytest.mark.django_db
class TestGameRepositoryOpeningCache:
    """Tests for opening cache functionality."""

    def test_cache_populated_on_init(self):
        """Opening cache is populated during init."""
        opening1 = OpeningFactory()
        opening2 = OpeningFactory()

        repo = GameRepository()

        assert len(repo._opening_cache) == 2
        assert repo._opening_cache[opening1.fen] == opening1.id
        assert repo._opening_cache[opening2.fen] == opening2.id

    def test_cache_miss_returns_none(self):
        """Unknown FEN returns None opening_id."""
        repo = GameRepository()
        game_data = make_game_data(opening_fen="unknown-fen")

        fields = repo._to_model_fields(game_data)

        assert fields["opening_id"] is None

    def test_cache_hit_returns_id(self):
        """Known FEN returns correct opening_id."""
        opening = OpeningFactory()
        repo = GameRepository()
        game_data = make_game_data(opening_fen=opening.fen)

        fields = repo._to_model_fields(game_data)

        assert fields["opening_id"] == opening.id


@pytest.mark.django_db
class TestGameRepositoryFieldMapping:
    """Tests for _to_model_fields method."""

    def test_all_fields_mapped(self):
        """All GameData fields are mapped correctly."""
        opening = OpeningFactory()
        repo = GameRepository()
        game_data = make_game_data(
            event="Test Event",
            site="Test Site",
            game_date=date(2024, 1, 15),
            round_num="5",
            white_player="Magnus",
            black_player="Hikaru",
            result="1-0",
            white_elo=2850,
            black_elo=2800,
            time_control="3+0",
            termination="Time forfeit",
            moves="1. e4 e5",
            opening_fen=opening.fen,
        )

        fields = repo._to_model_fields(game_data)

        assert fields["event"] == "Test Event"
        assert fields["site"] == "Test Site"
        assert fields["date"] == date(2024, 1, 15)
        assert fields["round"] == "5"
        assert fields["white_player"] == "Magnus"
        assert fields["black_player"] == "Hikaru"
        assert fields["result"] == "1-0"
        assert fields["white_elo"] == 2850
        assert fields["black_elo"] == 2800
        assert fields["time_control"] == "3+0"
        assert fields["termination"] == "Time forfeit"
        assert fields["moves"] == "1. e4 e5"
        assert fields["source_format"] == "pgn"
        assert fields["raw_headers"] == {"Event": "Test Event", "White": "Magnus"}
        assert fields["opening_id"] == opening.id

    def test_nullable_fields_preserved(self):
        """Nullable fields (date, elo) can be None."""
        repo = GameRepository()
        game_data = make_game_data(
            game_date=None,
            white_elo=None,
            black_elo=None,
        )

        fields = repo._to_model_fields(game_data)

        assert fields["date"] is None
        assert fields["white_elo"] is None
        assert fields["black_elo"] is None
