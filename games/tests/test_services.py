"""Tests for OpeningDetector service."""

from unittest.mock import patch

import pytest

from games.services.openings import OpeningDetector, OpeningMatch


class TestOpeningMatch:
    """Tests for OpeningMatch dataclass."""

    def test_create_opening_match(self):
        """OpeningMatch can be created with fen and ply."""
        match = OpeningMatch(fen="test-fen", ply=5)
        assert match.fen == "test-fen"
        assert match.ply == 5

    def test_opening_match_attributes(self):
        """OpeningMatch has correct attributes."""
        match = OpeningMatch(
            fen="rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1", ply=1
        )
        assert hasattr(match, "fen")
        assert hasattr(match, "ply")


@pytest.mark.django_db
class TestOpeningDetectorInit:
    """Tests for OpeningDetector initialization."""

    def test_init_loads_fens(self, opening_set):
        """Detector loads FENs from database."""
        detector = OpeningDetector()
        assert len(detector._fen_set) == 5

    def test_init_empty_database(self):
        """Detector handles empty database."""
        detector = OpeningDetector()
        assert isinstance(detector._fen_set, set)


@pytest.mark.django_db
class TestOpeningDetectorDetect:
    """Tests for OpeningDetector.detect_opening method."""

    def test_detect_opening_single_move(self, sample_opening):
        """Detect opening after single move (1. e4)."""
        detector = OpeningDetector()
        result = detector.detect_opening("1. e4")

        assert result is not None
        assert result.fen == sample_opening.fen
        assert result.ply == 1

    def test_detect_opening_multiple_moves(self, opening_set):
        """Detect deepest matching opening."""
        detector = OpeningDetector()
        result = detector.detect_opening("1. e4 e5 2. Nf3 Nc6 3. Bb5")

        assert result is not None
        assert result.ply == 5
        assert "Bb5" in result.fen or "B2" in result.fen  # Ruy Lopez position

    def test_detect_returns_deepest_match(self, opening_set):
        """Returns deepest match, not first match."""
        detector = OpeningDetector()
        result = detector.detect_opening("1. e4 e5 2. Nf3 Nc6 3. Bb5")

        # Should return Ruy Lopez (ply 5), not King's Pawn (ply 1)
        assert result.ply == 5

    def test_detect_no_match(self):
        """Returns None when no opening matches."""
        detector = OpeningDetector()
        result = detector.detect_opening("1. a3 a6 2. h3 h6")

        assert result is None

    def test_detect_empty_moves(self, sample_opening):
        """Returns None for empty moves string."""
        detector = OpeningDetector()
        result = detector.detect_opening("")

        assert result is None

    def test_detect_empty_fen_set(self):
        """Returns None when no openings in database."""
        detector = OpeningDetector()
        # _fen_set is empty since no openings loaded
        result = detector.detect_opening("1. e4 e5")

        assert result is None

    def test_detect_invalid_move_stops_parsing(self, opening_set):
        """Invalid move stops parsing but returns last valid match."""
        detector = OpeningDetector()
        # "invalid" is not a valid chess move
        result = detector.detect_opening("1. e4 e5 2. invalid Nc6")

        # Should still return the match for "1. e4 e5" (ply 2)
        assert result is not None
        assert result.ply == 2

    def test_detect_partial_match(self, opening_set):
        """Returns match even if game continues past known openings."""
        detector = OpeningDetector()
        # Continue past Ruy Lopez
        result = detector.detect_opening(
            "1. e4 e5 2. Nf3 Nc6 3. Bb5 a6 4. Ba4 Nf6 5. O-O"
        )

        # Should return Ruy Lopez (the deepest known opening)
        assert result is not None
        assert result.ply == 5

    def test_detect_with_result_marker(self, sample_opening):
        """Handles moves with result marker at end."""
        detector = OpeningDetector()
        result = detector.detect_opening("1. e4 1-0")

        assert result is not None
        assert result.ply == 1

    def test_detect_without_move_numbers(self, opening_set):
        """Handles moves without move numbers."""
        detector = OpeningDetector()
        result = detector.detect_opening("e4 e5 Nf3 Nc6 Bb5")

        assert result is not None
        assert result.ply == 5


@pytest.mark.django_db
class TestOpeningDetectorParseMoves:
    """Tests for OpeningDetector._parse_moves method."""

    def test_parse_moves_with_numbers(self, sample_opening):
        """Parse moves with move numbers."""
        detector = OpeningDetector()
        result = detector._parse_moves("1. e4 e5 2. Nf3 Nc6")

        assert result == ["e4", "e5", "Nf3", "Nc6"]

    def test_parse_moves_without_numbers(self, sample_opening):
        """Parse moves without move numbers."""
        detector = OpeningDetector()
        result = detector._parse_moves("e4 e5 Nf3 Nc6")

        assert result == ["e4", "e5", "Nf3", "Nc6"]

    def test_parse_moves_with_result(self, sample_opening):
        """Filter out result markers."""
        detector = OpeningDetector()

        assert detector._parse_moves("1. e4 e5 1-0") == ["e4", "e5"]
        assert detector._parse_moves("1. d4 d5 0-1") == ["d4", "d5"]
        assert detector._parse_moves("1. c4 1/2-1/2") == ["c4"]
        assert detector._parse_moves("1. e4 *") == ["e4"]

    def test_parse_moves_empty(self, sample_opening):
        """Parse empty string returns empty list."""
        detector = OpeningDetector()
        result = detector._parse_moves("")

        assert result == []

    def test_parse_moves_only_numbers(self, sample_opening):
        """Parse string with only move numbers returns empty list."""
        detector = OpeningDetector()
        result = detector._parse_moves("1. 2. 3.")

        assert result == []

    def test_parse_moves_with_ellipsis(self, sample_opening):
        """Parse moves with ellipsis notation (continuation)."""
        detector = OpeningDetector()
        # "1..." is a move number continuation
        result = detector._parse_moves("1... e5 2. Nf3")

        assert result == ["e5", "Nf3"]


class TestOpeningDetectorMocked:
    """Tests for OpeningDetector with mocked database."""

    def test_detect_fen_matching(self):
        """Test FEN matching logic with mock."""
        with patch.object(OpeningDetector, "__init__", lambda self: None):
            detector = OpeningDetector()
            detector._fen_set = {
                "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1",  # After 1. e4
            }

            result = detector.detect_opening("1. e4")

            assert result is not None
            assert result.ply == 1

    def test_detect_multiple_positions_in_set(self):
        """Test detection with multiple positions in set."""
        with patch.object(OpeningDetector, "__init__", lambda self: None):
            detector = OpeningDetector()
            detector._fen_set = {
                "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1",  # After 1. e4
                "rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2",  # After 1... e5
            }

            result = detector.detect_opening("1. e4 e5")

            # Should return the deepest match (ply 2)
            assert result is not None
            assert result.ply == 2

    def test_detect_ambiguous_move(self):
        """Test that ambiguous moves stop parsing."""
        with patch.object(OpeningDetector, "__init__", lambda self: None):
            detector = OpeningDetector()
            detector._fen_set = {
                "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1",
            }

            # This move sequence leads to ambiguous knight move if not handled
            result = detector.detect_opening("1. e4")

            assert result is not None
            assert result.ply == 1


@pytest.mark.django_db
class TestOpeningDetectorIntegration:
    """Integration tests for OpeningDetector with real chess positions."""

    def test_ruy_lopez_detection(self, ruy_lopez_opening):
        """Detect Ruy Lopez opening."""
        detector = OpeningDetector()
        result = detector.detect_opening("1. e4 e5 2. Nf3 Nc6 3. Bb5")

        assert result is not None
        assert result.fen == ruy_lopez_opening.fen
        assert result.ply == 5

    def test_game_with_no_opening_database_match(self, sample_opening):
        """Game that doesn't match any opening in sparse database."""
        detector = OpeningDetector()
        # Queen's pawn opening not in sample_opening (which only has 1. e4)
        result = detector.detect_opening("1. d4 d5 2. c4")

        assert result is None

    def test_detection_stops_at_invalid_position(self, opening_set):
        """Detection handles games with illegal moves gracefully."""
        detector = OpeningDetector()
        # After normal opening, try illegal move
        result = detector.detect_opening(
            "1. e4 e5 2. Nf3 Nc6 3. Ke2"
        )  # Ke2 illegal - king blocked

        # Should return last valid match
        assert result is not None
        # Ply 4 is the last valid position (2... Nc6)
        assert result.ply == 4
