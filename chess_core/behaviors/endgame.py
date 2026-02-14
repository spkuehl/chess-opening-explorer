"""Endgame detection derived from FEN."""

ENDGAME_THRESHOLD = 6
MINOR_OR_MAJOR_PIECES = "NBRQnbrq"


def is_endgame(fen: str) -> bool:
    """Return True if the position is in the endgame.

    Endgame is defined as ENDGAME_THRESHOLD or fewer minor or major
    pieces remaining on the board. Minor pieces are knights and
    bishops; major pieces are rooks and queens. Pawns and kings are
    not counted.

    Args:
        fen: A FEN string (only the first field, piece placement, is used).

    Returns:
        True if ENDGAME_THRESHOLD or fewer N/B/R/Q pieces remain, False otherwise.
    """
    piece_placement = fen.split()[0]
    count = sum(1 for c in piece_placement if c in MINOR_OR_MAJOR_PIECES)
    return count <= ENDGAME_THRESHOLD
