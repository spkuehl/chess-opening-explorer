"""Opening detection service for chess games."""

from dataclasses import dataclass

import chess

from chess_core.models import Opening
from chess_core.services.move_parsing import parse_san_moves


@dataclass
class OpeningMatch:
    """Result of opening detection.

    Attributes:
        fen: The FEN string of the matched opening position.
        ply: The ply (half-move) number where the match was found.
    """

    fen: str
    ply: int


class OpeningDetector:
    """Detects chess openings by matching FEN positions against the Opening table.

    The detector loads all known opening FENs into memory for fast lookup,
    then replays game moves to find the deepest matching opening position.
    """

    def __init__(self, fen_set: set[str] | None = None) -> None:
        """Load opening FENs for fast lookup.

        When fen_set is provided, it is used as the set of known FENs and
        no database query is performed (useful when reusing a repository-level
        cache). When fen_set is None, FENs are loaded from the Opening table.
        """
        if fen_set is not None:
            self._fen_set = fen_set
        else:
            self._fen_set = set(Opening.objects.values_list("fen", flat=True))

    def detect_opening(self, moves: str) -> OpeningMatch | None:
        """Detect the opening played in a game by its move string.

        Replays the moves on a board, generates FEN after each move,
        and returns the deepest (latest) matching opening.

        Args:
            moves: A move string in SAN format, e.g., "1. e4 e5 2. Nf3 Nc6".

        Returns:
            An OpeningMatch with the FEN and ply of the deepest match,
            or None if no opening was found.
        """
        if not moves or not self._fen_set:
            return None

        board = chess.Board()
        last_match: OpeningMatch | None = None
        ply = 0

        parsed_moves = parse_san_moves(moves)

        for move_san in parsed_moves:
            try:
                move = board.parse_san(move_san)
                board.push(move)
                ply += 1

                # Get full FEN for exact matching
                full_fen = board.fen()

                if full_fen in self._fen_set:
                    last_match = OpeningMatch(fen=full_fen, ply=ply)

            except (chess.InvalidMoveError, chess.AmbiguousMoveError):
                break

        return last_match
