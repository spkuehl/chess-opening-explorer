"""Tests for management commands."""

import tempfile
from io import StringIO
from pathlib import Path

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from games.models import Game, Opening

from .factories import GameFactory, OpeningFactory


@pytest.mark.django_db
class TestImportGamesCommand:
    """Tests for import_games management command."""

    def test_import_single_game(self, sample_pgn_content: str):
        """Import PGN file with single game."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".pgn", delete=False) as f:
            f.write(sample_pgn_content)
            path = f.name

        out = StringIO()
        call_command("import_games", path, stdout=out)

        assert Game.objects.count() == 1
        assert "Processed 1 games" in out.getvalue()

    def test_import_multiple_games(self, multi_game_pgn: str):
        """Import PGN file with multiple games."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".pgn", delete=False) as f:
            f.write(multi_game_pgn)
            path = f.name

        out = StringIO()
        call_command("import_games", path, stdout=out)

        assert Game.objects.count() == 3
        assert "Processed 3 games" in out.getvalue()

    def test_import_file_not_found(self):
        """Import non-existent file raises CommandError."""
        with pytest.raises(CommandError, match="File not found"):
            call_command("import_games", "/nonexistent/file.pgn")

    def test_import_with_batch_size(self, multi_game_pgn: str):
        """Import with custom batch size."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".pgn", delete=False) as f:
            f.write(multi_game_pgn)
            path = f.name

        out = StringIO()
        call_command("import_games", path, "--batch-size", "1", stdout=out)

        assert Game.objects.count() == 3
        assert "Batch size: 1" in out.getvalue()

    def test_import_with_opening_detection(self, sample_pgn_content: str):
        """Import detects openings when Opening table populated."""
        # Create an opening that matches the game
        Opening.objects.create(
            fen="rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1",
            eco_code="B00",
            name="King's Pawn Game",
            moves="1. e4",
            ply_count=1,
        )

        with tempfile.NamedTemporaryFile(mode="w", suffix=".pgn", delete=False) as f:
            f.write(sample_pgn_content)
            path = f.name

        out = StringIO()
        call_command("import_games", path, stdout=out)

        game = Game.objects.first()
        assert game.opening is not None
        assert game.opening.eco_code == "B00"

    def test_import_skips_duplicates(self, sample_pgn_content: str):
        """Import skips duplicate games."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".pgn", delete=False) as f:
            f.write(sample_pgn_content)
            path = f.name

        # Import twice
        call_command("import_games", path, stdout=StringIO())
        out = StringIO()
        call_command("import_games", path, stdout=out)

        assert Game.objects.count() == 1
        assert "New games added: 0" in out.getvalue()

    def test_import_reports_statistics(self, sample_pgn_content: str):
        """Import reports processing statistics."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".pgn", delete=False) as f:
            f.write(sample_pgn_content)
            path = f.name

        out = StringIO()
        call_command("import_games", path, stdout=out)
        output = out.getvalue()

        assert "Processed" in output
        assert "games" in output
        assert "seconds" in output


@pytest.mark.django_db
class TestLoadOpeningsCommand:
    """Tests for load_openings management command."""

    def test_load_openings_from_data_directory(self):
        """Load openings from default data directory."""
        out = StringIO()
        call_command("load_openings", stdout=out)

        # Should load openings from all ECO files
        assert Opening.objects.count() > 0
        assert "Loading openings from:" in out.getvalue()

    def test_load_openings_reports_per_file(self):
        """Load command reports loaded count per file."""
        out = StringIO()
        call_command("load_openings", stdout=out)
        output = out.getvalue()

        assert "ecoA.json" in output
        assert "ecoB.json" in output
        assert "Loaded:" in output

    def test_load_openings_with_clear(self):
        """Load with --clear deletes existing openings."""
        # Create some openings first
        OpeningFactory.create_batch(3)
        assert Opening.objects.count() == 3

        out = StringIO()
        call_command("load_openings", "--clear", stdout=out)

        assert "Clearing existing openings..." in out.getvalue()
        # Should have ECO openings, not the factory ones
        assert Opening.objects.count() > 3

    def test_load_openings_handles_duplicates(self):
        """Load handles duplicate FENs gracefully."""
        # Load once
        call_command("load_openings", stdout=StringIO())
        count_first = Opening.objects.count()

        # Load again (without clear)
        out = StringIO()
        call_command("load_openings", stdout=out)

        # Count should be same (duplicates skipped)
        assert Opening.objects.count() == count_first
        assert "Skipped (duplicates):" in out.getvalue()

    def test_load_openings_custom_data_dir(self, tmp_path: Path):
        """Load from custom data directory."""
        # This should fail because directory is empty
        err = StringIO()
        call_command("load_openings", "--data-dir", str(tmp_path), stderr=err)

        assert "Missing files:" in err.getvalue()


@pytest.mark.django_db
class TestDetectOpeningsCommand:
    """Tests for detect_openings management command."""

    def test_detect_no_games(self):
        """Detect with no games reports nothing to process."""
        out = StringIO()
        call_command("detect_openings", stdout=out)

        assert "No games to process" in out.getvalue()

    def test_detect_games_without_openings(self):
        """Detect openings for games without them."""
        # Create a game without opening
        GameFactory(opening=None, moves="1. e4 e5")

        # Create matching opening
        Opening.objects.create(
            fen="rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1",
            eco_code="B00",
            name="King's Pawn Game",
            moves="1. e4",
            ply_count=1,
        )

        out = StringIO()
        call_command("detect_openings", stdout=out)

        game = Game.objects.first()
        assert game.opening is not None
        assert "updated 1 with openings" in out.getvalue()

    def test_detect_skips_games_with_openings(self):
        """Detect skips games that already have openings."""
        opening = OpeningFactory()
        GameFactory(opening=opening)

        out = StringIO()
        call_command("detect_openings", stdout=out)

        assert "No games to process" in out.getvalue()

    def test_detect_force_redetects_all(self):
        """Detect with --force re-detects all games."""
        opening = OpeningFactory()
        GameFactory(opening=opening, moves="1. e4 e5")

        # Create a different opening that matches the moves
        Opening.objects.create(
            fen="rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1",
            eco_code="B00",
            name="King's Pawn Game",
            moves="1. e4",
            ply_count=1,
        )

        out = StringIO()
        call_command("detect_openings", "--force", stdout=out)

        assert "Processing all games (--force mode)" in out.getvalue()

    def test_detect_with_batch_size(self):
        """Detect with custom batch size."""
        # Create games without openings
        for i in range(5):
            GameFactory(opening=None, moves="1. d4", source_id=f"batch-test-{i}")

        out = StringIO()
        call_command("detect_openings", "--batch-size", "2", stdout=out)

        assert "Batch size: 2" in out.getvalue()

    def test_detect_reports_statistics(self):
        """Detect reports processing statistics."""
        GameFactory(opening=None, moves="1. e4")
        Opening.objects.create(
            fen="rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1",
            eco_code="B00",
            name="King's Pawn Game",
            moves="1. e4",
            ply_count=1,
        )

        out = StringIO()
        call_command("detect_openings", stdout=out)
        output = out.getvalue()

        assert "Completed in" in output
        assert "Games processed:" in output
        assert "Games updated with openings:" in output
        assert "Games with openings:" in output

    def test_detect_handles_no_match(self):
        """Detect handles games with no matching opening."""
        # Create game with unusual opening
        GameFactory(opening=None, moves="1. h4 h5 2. g4")

        out = StringIO()
        call_command("detect_openings", stdout=out)

        game = Game.objects.first()
        assert game.opening is None
        assert "updated 0 with openings" in out.getvalue()


@pytest.mark.django_db
class TestCommandIntegration:
    """Integration tests combining multiple commands."""

    def test_load_then_import_with_detection(self, sample_pgn_content: str):
        """Load openings, then import games with detection."""
        # Step 1: Load openings
        call_command("load_openings", stdout=StringIO())
        opening_count = Opening.objects.count()
        assert opening_count > 0

        # Step 2: Import games (should detect openings)
        with tempfile.NamedTemporaryFile(mode="w", suffix=".pgn", delete=False) as f:
            f.write(sample_pgn_content)
            path = f.name

        call_command("import_games", path, stdout=StringIO())

        # Game should have opening detected
        game = Game.objects.first()
        assert game.opening is not None

    def test_import_then_backfill(self, sample_pgn_content: str):
        """Import games first, then backfill openings."""
        # Step 1: Import without openings in database
        with tempfile.NamedTemporaryFile(mode="w", suffix=".pgn", delete=False) as f:
            f.write(sample_pgn_content)
            path = f.name

        call_command("import_games", path, stdout=StringIO())
        game = Game.objects.first()
        assert game.opening is None  # No openings in DB

        # Step 2: Load openings
        call_command("load_openings", stdout=StringIO())

        # Step 3: Backfill
        call_command("detect_openings", stdout=StringIO())

        game.refresh_from_db()
        assert game.opening is not None
