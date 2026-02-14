"""Tests for chess_core.behaviors.is_endgame."""

import pytest

from chess_core.behaviors import ENDGAME_THRESHOLD, is_endgame

FEN_START = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
FEN_KR_VS_K = "4r3/8/8/8/8/8/8/4K3 w - - 0 1"
FEN_SIX_PIECES = "3r1b2/2n2n2/1q1b4/8/8/8/8/4K3 w - - 0 1"
FEN_SEVEN_PIECES = "3r1b2/2n2n2/1q1b1n2/8/8/8/8/4K3 w - - 0 1"
FEN_PIECE_PLACEMENT_ONLY = "4r3/8/8/8/8/8/8/4K3"


class TestEndgameThreshold:
    """Tests for ENDGAME_THRESHOLD constant."""

    def test_endgame_threshold_is_six(self) -> None:
        """ENDGAME_THRESHOLD is 6."""
        assert ENDGAME_THRESHOLD == 6


class TestIsEndgame:
    """Tests for is_endgame function."""

    def test_start_position_not_endgame(self) -> None:
        """Full starting position (16 minor/major pieces) is not endgame."""
        assert is_endgame(FEN_START) is False

    def test_single_rook_is_endgame(self) -> None:
        """K+R vs K (1 minor/major piece) is endgame."""
        assert is_endgame(FEN_KR_VS_K) is True

    def test_six_pieces_is_endgame(self) -> None:
        """Exactly 6 minor/major pieces is endgame."""
        assert is_endgame(FEN_SIX_PIECES) is True

    def test_seven_pieces_not_endgame(self) -> None:
        """Exactly 7 minor/major pieces is not endgame."""
        assert is_endgame(FEN_SEVEN_PIECES) is False

    def test_zero_pieces_is_endgame(self) -> None:
        """Bare kings (0 minor/major pieces) is endgame."""
        assert is_endgame("4k3/8/8/8/8/8/8/4K3 w - - 0 1") is True

    def test_uses_only_piece_placement_field(self) -> None:
        """Only the first FEN field (piece placement) is used."""
        assert is_endgame(FEN_PIECE_PLACEMENT_ONLY) is True
        assert is_endgame(FEN_KR_VS_K) is True

    def test_ignores_pawns_and_kings(self) -> None:
        """Only knights, bishops, rooks, and queens are counted."""
        # Many pawns and both kings, but only 2 rooks
        fen = "r3k2r/pppppppp/8/8/8/8/PPPPPPPP/R3K2R w KQkq - 0 1"
        assert is_endgame(fen) is True
