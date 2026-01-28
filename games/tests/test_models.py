"""Tests for Django models."""

from datetime import date

import pytest
from django.db import IntegrityError

from games.models import Game, Opening

from .factories import GameFactory, OpeningFactory


@pytest.mark.django_db
class TestOpeningModel:
    """Tests for the Opening model."""

    def test_str_representation(self):
        """Opening __str__ returns 'eco_code: name'."""
        opening = OpeningFactory(eco_code="B33", name="Sicilian: Sveshnikov")
        assert str(opening) == "B33: Sicilian: Sveshnikov"

    def test_fen_unique_constraint(self):
        """Duplicate FEN raises IntegrityError."""
        fen = "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1"
        OpeningFactory(fen=fen)
        with pytest.raises(IntegrityError):
            OpeningFactory(fen=fen)

    def test_required_fields(self):
        """Opening can be created with all required fields."""
        opening = Opening.objects.create(
            fen="test-fen-unique",
            eco_code="A00",
            name="Test Opening",
            moves="1. e4",
            ply_count=1,
        )
        assert opening.pk is not None

    def test_optional_fields_defaults(self):
        """Optional fields have correct defaults."""
        opening = Opening.objects.create(
            fen="test-fen-defaults",
            eco_code="A00",
            name="Test",
            moves="1. e4",
            ply_count=1,
        )
        assert opening.source == ""
        assert opening.is_eco_root is False

    def test_eco_code_indexed(self):
        """eco_code field is indexed."""
        # Verify the index exists by checking model meta
        assert any("eco_code" in str(idx.fields) for idx in Opening._meta.indexes)

    def test_name_indexed(self):
        """name field is indexed."""
        assert any("name" in str(idx.fields) for idx in Opening._meta.indexes)


@pytest.mark.django_db
class TestGameModel:
    """Tests for the Game model."""

    def test_str_representation(self):
        """Game __str__ returns 'white vs black (date)'."""
        game = GameFactory(
            white_player="Magnus",
            black_player="Hikaru",
            date=date(2024, 1, 15),
        )
        assert str(game) == "Magnus vs Hikaru (2024-01-15)"

    def test_str_with_none_date(self):
        """Game __str__ handles None date."""
        game = GameFactory(
            white_player="Magnus",
            black_player="Hikaru",
            date=None,
        )
        assert str(game) == "Magnus vs Hikaru (None)"

    def test_source_id_unique_constraint(self):
        """Duplicate source_id raises IntegrityError."""
        GameFactory(source_id="unique-game-id")
        with pytest.raises(IntegrityError):
            GameFactory(source_id="unique-game-id")

    def test_opening_foreign_key_nullable(self):
        """opening FK can be null."""
        game = GameFactory(opening=None)
        assert game.opening is None
        assert game.pk is not None

    def test_opening_foreign_key_assignment(self):
        """opening FK can be assigned to an Opening."""
        opening = OpeningFactory()
        game = GameFactory(opening=opening)
        assert game.opening == opening
        assert game.opening.eco_code == opening.eco_code

    def test_opening_on_delete_set_null(self):
        """Deleting Opening sets Game.opening to NULL."""
        opening = OpeningFactory()
        game = GameFactory(opening=opening)
        opening_id = opening.pk

        # Delete the opening
        opening.delete()

        # Refresh game from database
        game.refresh_from_db()
        assert game.opening is None
        assert not Opening.objects.filter(pk=opening_id).exists()

    def test_required_fields_minimal(self):
        """Game can be created with minimal required fields."""
        game = Game.objects.create(
            source_id="minimal-game",
            white_player="White",
            black_player="Black",
            result="1-0",
            moves="1. e4",
            source_format="pgn",
        )
        assert game.pk is not None

    def test_optional_fields_blank(self):
        """Optional text fields accept blank values."""
        game = Game.objects.create(
            source_id="blank-fields-game",
            white_player="White",
            black_player="Black",
            result="1-0",
            moves="1. e4",
            source_format="pgn",
            event="",
            site="",
            round="",
            time_control="",
            termination="",
        )
        assert game.event == ""
        assert game.site == ""

    def test_nullable_fields(self):
        """Nullable fields accept None."""
        game = Game.objects.create(
            source_id="nullable-fields-game",
            white_player="White",
            black_player="Black",
            result="1-0",
            moves="1. e4",
            source_format="pgn",
            date=None,
            white_elo=None,
            black_elo=None,
        )
        assert game.date is None
        assert game.white_elo is None
        assert game.black_elo is None

    def test_raw_headers_json_field(self):
        """raw_headers stores JSON data correctly."""
        headers = {"Event": "Test", "Custom": "Value"}
        game = GameFactory(raw_headers=headers)
        game.refresh_from_db()
        assert game.raw_headers == headers

    def test_raw_headers_default_empty_dict(self):
        """raw_headers defaults to empty dict."""
        game = Game.objects.create(
            source_id="default-headers-game",
            white_player="White",
            black_player="Black",
            result="1-0",
            moves="1. e4",
            source_format="pgn",
        )
        assert game.raw_headers == {}

    def test_created_at_auto_set(self):
        """created_at is automatically set on creation."""
        game = GameFactory()
        assert game.created_at is not None

    def test_source_id_indexed(self):
        """source_id field is indexed."""
        field = Game._meta.get_field("source_id")
        assert field.db_index is True

    def test_date_indexed(self):
        """date field is indexed."""
        field = Game._meta.get_field("date")
        assert field.db_index is True

    def test_white_player_indexed(self):
        """white_player field is indexed."""
        field = Game._meta.get_field("white_player")
        assert field.db_index is True

    def test_black_player_indexed(self):
        """black_player field is indexed."""
        field = Game._meta.get_field("black_player")
        assert field.db_index is True


@pytest.mark.django_db
class TestModelRelationships:
    """Tests for model relationships."""

    def test_game_opening_relationship(self):
        """Game.opening relationship works correctly."""
        opening = OpeningFactory(name="Italian Game")
        game1 = GameFactory(opening=opening)
        game2 = GameFactory(opening=opening)

        # Access from game side
        assert game1.opening.name == "Italian Game"
        assert game2.opening.name == "Italian Game"

        # Access from opening side (reverse relation)
        games = opening.game_set.all()
        assert game1 in games
        assert game2 in games

    def test_opening_game_count(self):
        """Can count games per opening."""
        opening = OpeningFactory()
        GameFactory.create_batch(5, opening=opening)

        assert opening.game_set.count() == 5
