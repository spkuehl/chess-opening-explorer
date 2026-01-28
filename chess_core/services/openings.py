"""Opening detection service for chess games."""

from dataclasses import dataclass

import chess

from chess_core.models import Opening


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

    def __init__(self) -> None:
        """Load all Opening FENs into memory for fast lookup."""
        self._fen_set: set[str] = set(Opening.objects.values_list("fen", flat=True))

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

        # Parse moves from the move string
        parsed_moves = self._parse_moves(moves)

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
                # Stop parsing if we encounter an invalid move
                break

        return last_match

    def _parse_moves(self, moves: str) -> list[str]:
        """Parse a move string into individual SAN moves.

        Args:
            moves: A move string like "1. e4 e5 2. Nf3 Nc6" or "e4 e5 Nf3 Nc6".

        Returns:
            A list of SAN moves like ["e4", "e5", "Nf3", "Nc6"].
        """
        tokens = moves.split()
        san_moves = []

        for token in tokens:
            # Skip move numbers (e.g., "1.", "2.", "1...")
            if token.endswith(".") or token.replace(".", "").isdigit():
                continue
            # Skip result markers
            if token in ("1-0", "0-1", "1/2-1/2", "*"):
                continue
            san_moves.append(token)

        return san_moves
