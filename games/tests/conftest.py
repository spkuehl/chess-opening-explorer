"""Shared fixtures for games app tests."""

import tempfile
from pathlib import Path

import pytest

from games.models import Opening


@pytest.fixture
def sample_pgn_content() -> str:
    """Valid PGN with one game."""
    return """[Event "Test Event"]
[Site "Test Site"]
[Date "2024.01.15"]
[Round "1"]
[White "Player One"]
[Black "Player Two"]
[Result "1-0"]
[WhiteElo "2500"]
[BlackElo "2400"]
[TimeControl "300+0"]
[Termination "Normal"]

1. e4 e5 2. Nf3 Nc6 3. Bb5 a6 4. Ba4 Nf6 5. O-O Be7 1-0
"""


@pytest.fixture
def multi_game_pgn() -> str:
    """PGN with multiple games."""
    return """[Event "Game 1"]
[Site "Site 1"]
[Date "2024.01.15"]
[Round "1"]
[White "White1"]
[Black "Black1"]
[Result "1-0"]

1. e4 e5 1-0

[Event "Game 2"]
[Site "Site 2"]
[Date "2024.01.16"]
[Round "2"]
[White "White2"]
[Black "Black2"]
[Result "0-1"]

1. d4 d5 0-1

[Event "Game 3"]
[Site "Site 3"]
[Date "2024.01.17"]
[Round "3"]
[White "White3"]
[Black "Black3"]
[Result "1/2-1/2"]

1. c4 c5 1/2-1/2
"""


@pytest.fixture
def malformed_pgn() -> str:
    """Invalid PGN for error handling tests."""
    return """[Event "Broken Game"]
[White "Player"]
[Result "1-0"]

1. e4 e5 2. invalid_move Nc6 1-0
"""


@pytest.fixture
def pgn_with_missing_headers() -> str:
    """PGN with minimal headers."""
    return """[Result "*"]

1. e4 e5 *
"""


@pytest.fixture
def pgn_with_partial_date() -> str:
    """PGN with partial date (unknown day/month)."""
    return """[Event "Test"]
[Site "Test"]
[Date "2024.??.??"]
[Round "1"]
[White "White"]
[Black "Black"]
[Result "1-0"]

1. e4 1-0
"""


@pytest.fixture
def temp_pgn_file(sample_pgn_content: str) -> Path:
    """Create a temporary PGN file for testing."""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".pgn", delete=False, encoding="utf-8"
    ) as f:
        f.write(sample_pgn_content)
        return Path(f.name)


@pytest.fixture
def temp_multi_game_pgn_file(multi_game_pgn: str) -> Path:
    """Create a temporary PGN file with multiple games."""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".pgn", delete=False, encoding="utf-8"
    ) as f:
        f.write(multi_game_pgn)
        return Path(f.name)


@pytest.fixture
def sample_opening(db) -> Opening:
    """Create a sample Opening for testing."""
    return Opening.objects.create(
        fen="rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1",
        eco_code="B00",
        name="King's Pawn Game",
        moves="1. e4",
        ply_count=1,
        source="test",
        is_eco_root=True,
    )


@pytest.fixture
def ruy_lopez_opening(db) -> Opening:
    """Create Ruy Lopez opening for testing."""
    return Opening.objects.create(
        fen="r1bqkbnr/pppp1ppp/2n5/1B2p3/4P3/5N2/PPPP1PPP/RNBQK2R b KQkq - 3 3",
        eco_code="C60",
        name="Ruy Lopez",
        moves="1. e4 e5 2. Nf3 Nc6 3. Bb5",
        ply_count=5,
        source="test",
        is_eco_root=True,
    )


@pytest.fixture
def opening_set(db) -> list[Opening]:
    """Create a set of openings for comprehensive testing."""
    openings = [
        Opening(
            fen="rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1",
            eco_code="B00",
            name="King's Pawn Game",
            moves="1. e4",
            ply_count=1,
        ),
        Opening(
            fen="rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2",
            eco_code="C20",
            name="King's Pawn Game: Open Game",
            moves="1. e4 e5",
            ply_count=2,
        ),
        Opening(
            fen="rnbqkbnr/pppp1ppp/8/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R b KQkq - 1 2",
            eco_code="C40",
            name="King's Knight Opening",
            moves="1. e4 e5 2. Nf3",
            ply_count=3,
        ),
        Opening(
            fen="r1bqkbnr/pppp1ppp/2n5/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 2 3",
            eco_code="C44",
            name="King's Knight Opening: Normal Variation",
            moves="1. e4 e5 2. Nf3 Nc6",
            ply_count=4,
        ),
        Opening(
            fen="r1bqkbnr/pppp1ppp/2n5/1B2p3/4P3/5N2/PPPP1PPP/RNBQK2R b KQkq - 3 3",
            eco_code="C60",
            name="Ruy Lopez",
            moves="1. e4 e5 2. Nf3 Nc6 3. Bb5",
            ply_count=5,
        ),
    ]
    return Opening.objects.bulk_create(openings)
