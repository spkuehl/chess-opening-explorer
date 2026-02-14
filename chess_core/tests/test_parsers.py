"""Tests for PGN parser."""

import tempfile
from datetime import date
from pathlib import Path

import pytest

from chess_core.parsers.base import GameData
from chess_core.parsers.pgn import PGNParser


class TestPGNParserInit:
    """Tests for PGNParser initialization."""

    def test_init(self):
        """Parser initializes with no arguments."""
        parser = PGNParser()
        assert parser is not None


class TestPGNParserParse:
    """Tests for PGNParser.parse method."""

    def test_parse_single_game(self, temp_pgn_file: Path):
        """Parse PGN file with one game."""
        parser = PGNParser()
        games = list(parser.parse(temp_pgn_file))

        assert len(games) == 1
        assert games[0].white_player == "Player One"
        assert games[0].black_player == "Player Two"
        assert games[0].result == "1-0"

    def test_parse_multiple_games(self, temp_multi_game_pgn_file: Path):
        """Parse PGN file with multiple games."""
        parser = PGNParser()
        games = list(parser.parse(temp_multi_game_pgn_file))

        assert len(games) == 3
        assert games[0].white_player == "White1"
        assert games[1].white_player == "White2"
        assert games[2].white_player == "White3"

    def test_parse_yields_gamedata(self, temp_pgn_file: Path):
        """Parser yields GameData instances."""
        parser = PGNParser()
        games = list(parser.parse(temp_pgn_file))

        assert all(isinstance(g, GameData) for g in games)

    def test_parse_empty_file(self):
        """Parse empty PGN file returns no games."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".pgn", delete=False) as f:
            f.write("")
            path = Path(f.name)

        parser = PGNParser()
        games = list(parser.parse(path))

        assert len(games) == 0

    def test_parse_file_not_found(self):
        """Parse non-existent file raises FileNotFoundError."""
        parser = PGNParser()
        with pytest.raises(FileNotFoundError):
            list(parser.parse(Path("/nonexistent/file.pgn")))

    def test_parse_extracts_all_fields(self, temp_pgn_file: Path):
        """All GameData fields are populated from PGN."""
        parser = PGNParser()
        game = list(parser.parse(temp_pgn_file))[0]

        assert game.source_id  # Non-empty hash
        assert game.event == "Test Event"
        assert game.site == "Test Site"
        assert game.date == date(2024, 1, 15)
        assert game.round == "1"
        assert game.white_player == "Player One"
        assert game.black_player == "Player Two"
        assert game.result == "1-0"
        assert game.white_elo == 2500
        assert game.black_elo == 2400
        assert game.time_control == "300+0"
        assert game.termination == "Normal"
        assert "e4" in game.moves
        assert game.source_format == "pgn"
        assert "Event" in game.raw_headers

    def test_parse_with_path_string(self, temp_pgn_file: Path):
        """Parser accepts string path."""
        parser = PGNParser()
        games = list(parser.parse(str(temp_pgn_file)))

        assert len(games) == 1


class TestPGNParserDateParsing:
    """Tests for date parsing in PGNParser."""

    def test_parse_date_valid(self):
        """Parse valid date string."""
        parser = PGNParser()
        result = parser._parse_date("2024.01.15")
        assert result == date(2024, 1, 15)

    def test_parse_date_partial_day_unknown(self):
        """Parse date with unknown day."""
        parser = PGNParser()
        result = parser._parse_date("2024.01.??")
        assert result == date(2024, 1, 1)

    def test_parse_date_partial_month_day_unknown(self):
        """Parse date with unknown month and day."""
        parser = PGNParser()
        result = parser._parse_date("2024.??.??")
        assert result == date(2024, 1, 1)

    def test_parse_date_all_unknown(self):
        """Parse date with all parts unknown returns None."""
        parser = PGNParser()
        result = parser._parse_date("????.??.??")
        assert result is None

    def test_parse_date_empty_string(self):
        """Parse empty date string returns None."""
        parser = PGNParser()
        result = parser._parse_date("")
        assert result is None

    def test_parse_date_invalid_format(self):
        """Parse invalid date format returns None."""
        parser = PGNParser()
        result = parser._parse_date("invalid-date")
        assert result is None

    def test_parse_date_wrong_parts(self):
        """Parse date with wrong number of parts returns None."""
        parser = PGNParser()
        result = parser._parse_date("2024.01")
        assert result is None

    def test_parse_date_invalid_numbers(self):
        """Parse date with invalid numbers returns None."""
        parser = PGNParser()
        result = parser._parse_date("2024.13.45")  # Invalid month/day
        assert result is None


class TestPGNParserEloParsing:
    """Tests for Elo parsing in PGNParser."""

    def test_parse_int_valid(self):
        """Parse valid integer string."""
        parser = PGNParser()
        assert parser._parse_int("2800") == 2800

    def test_parse_int_question_mark(self):
        """Parse '?' returns None."""
        parser = PGNParser()
        assert parser._parse_int("?") is None

    def test_parse_int_dash(self):
        """Parse '-' returns None."""
        parser = PGNParser()
        assert parser._parse_int("-") is None

    def test_parse_int_none(self):
        """Parse None returns None."""
        parser = PGNParser()
        assert parser._parse_int(None) is None

    def test_parse_int_empty_string(self):
        """Parse empty string returns None."""
        parser = PGNParser()
        assert parser._parse_int("") is None

    def test_parse_int_invalid_string(self):
        """Parse non-numeric string returns None."""
        parser = PGNParser()
        assert parser._parse_int("abc") is None

    def test_parse_int_float_string(self):
        """Parse float string returns None."""
        parser = PGNParser()
        assert parser._parse_int("2800.5") is None


class TestPGNParserSourceIdGeneration:
    """Tests for source ID generation."""

    def test_source_id_deterministic(self, temp_pgn_file: Path):
        """Same game produces same source_id."""
        parser = PGNParser()
        games1 = list(parser.parse(temp_pgn_file))
        games2 = list(parser.parse(temp_pgn_file))

        assert games1[0].source_id == games2[0].source_id

    def test_source_id_unique_for_different_games(self, temp_multi_game_pgn_file: Path):
        """Different games produce different source_ids."""
        parser = PGNParser()
        games = list(parser.parse(temp_multi_game_pgn_file))

        source_ids = [g.source_id for g in games]
        assert len(source_ids) == len(set(source_ids))  # All unique

    def test_source_id_is_hash(self, temp_pgn_file: Path):
        """source_id is a hex hash string."""
        parser = PGNParser()
        game = list(parser.parse(temp_pgn_file))[0]

        assert len(game.source_id) == 64  # SHA-256 truncated
        assert all(c in "0123456789abcdef" for c in game.source_id)


class TestPGNParserMissingHeaders:
    """Tests for handling missing headers."""

    def test_parse_missing_white_player(self):
        """Missing White header gets python-chess default '?'."""
        pgn = """[Event "Test"]
[Black "Player"]
[Result "1-0"]

1. e4 1-0
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".pgn", delete=False) as f:
            f.write(pgn)
            path = Path(f.name)

        parser = PGNParser()
        game = list(parser.parse(path))[0]

        # python-chess returns "?" for missing required headers
        assert game.white_player == "?"

    def test_parse_missing_black_player(self):
        """Missing Black header gets python-chess default '?'."""
        pgn = """[Event "Test"]
[White "Player"]
[Result "1-0"]

1. e4 1-0
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".pgn", delete=False) as f:
            f.write(pgn)
            path = Path(f.name)

        parser = PGNParser()
        game = list(parser.parse(path))[0]

        # python-chess returns "?" for missing required headers
        assert game.black_player == "?"

    def test_parse_missing_result(self):
        """Missing Result header defaults to '*'."""
        pgn = """[Event "Test"]
[White "White"]
[Black "Black"]

1. e4 e5
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".pgn", delete=False) as f:
            f.write(pgn)
            path = Path(f.name)

        parser = PGNParser()
        game = list(parser.parse(path))[0]

        assert game.result == "*"

    def test_parse_missing_optional_headers(self, pgn_with_missing_headers: str):
        """Missing optional headers default correctly."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".pgn", delete=False) as f:
            f.write(pgn_with_missing_headers)
            path = Path(f.name)

        parser = PGNParser()
        game = list(parser.parse(path))[0]

        # python-chess returns "?" for missing standard headers
        assert game.event == "?"
        assert game.site == "?"
        assert game.date is None  # "?" in date triggers partial date parsing
        assert game.round == "?"
        assert game.white_elo is None
        assert game.black_elo is None
        assert game.time_control is None
        assert game.termination is None


class TestPGNParserMoveExtraction:
    """Tests for move text extraction."""

    def test_extract_moves(self, temp_pgn_file: Path):
        """Moves are extracted correctly."""
        parser = PGNParser()
        game = list(parser.parse(temp_pgn_file))[0]

        # Should contain the moves without result
        assert "e4" in game.moves
        assert "e5" in game.moves
        assert "Nf3" in game.moves

    def test_extract_moves_no_variations(self):
        """Variations are not included in moves."""
        pgn = """[Event "Test"]
[White "White"]
[Black "Black"]
[Result "1-0"]

1. e4 e5 (1... c5 2. Nf3) 2. Nf3 Nc6 1-0
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".pgn", delete=False) as f:
            f.write(pgn)
            path = Path(f.name)

        parser = PGNParser()
        game = list(parser.parse(path))[0]

        # Main line should be present
        assert "e4" in game.moves
        assert "e5" in game.moves
        # Variation (c5) should not be present
        assert "c5" not in game.moves


class TestPGNParserRawHeaders:
    """Tests for raw headers preservation."""

    def test_raw_headers_preserved(self, temp_pgn_file: Path):
        """All original headers are preserved in raw_headers."""
        parser = PGNParser()
        game = list(parser.parse(temp_pgn_file))[0]

        assert game.raw_headers["Event"] == "Test Event"
        assert game.raw_headers["Site"] == "Test Site"
        assert game.raw_headers["White"] == "Player One"
        assert game.raw_headers["Black"] == "Player Two"
        assert game.raw_headers["WhiteElo"] == "2500"
        assert game.raw_headers["BlackElo"] == "2400"

    def test_raw_headers_is_dict(self, temp_pgn_file: Path):
        """raw_headers is a proper dict."""
        parser = PGNParser()
        game = list(parser.parse(temp_pgn_file))[0]

        assert isinstance(game.raw_headers, dict)
