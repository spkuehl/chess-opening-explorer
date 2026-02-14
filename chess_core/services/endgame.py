"""Endgame detection service for chess games."""

from dataclasses import dataclass

import chess

from chess_core.behaviors import is_endgame
from chess_core.services.move_parsing import parse_san_moves


@dataclass
class EndgameEntry:
    """The ply and FEN where a game first enters the endgame.

    Attributes:
        fen: The FEN string of the position when endgame is first reached.
        ply: The ply (half-move) number when endgame is first reached.
    """

    fen: str
    ply: int


class EndgameDetector:
    """Detects when a game enters the endgame by replaying moves.

    Replays the game on a board and after each move checks whether
    the position qualifies as endgame (6 or fewer minor/major pieces).
    Returns the first ply and FEN at which that condition is met.
    """

    def detect_endgame(self, moves: str) -> EndgameEntry | None:
        """Detect the ply and FEN at which the game first enters endgame.

        Replays the moves on a board, checks the position after each
        move, and returns the first position that is in the endgame.

        Args:
            moves: A move string in SAN format, e.g., "1. e4 e5 2. Nf3 Nc6".

        Returns:
            An EndgameEntry with the FEN and ply of the first endgame
            position, or None if the game never enters endgame.
        """
        if not moves:
            return None

        board = chess.Board()
        parsed_moves = parse_san_moves(moves)
        ply = 0

        for move_san in parsed_moves:
            try:
                move = board.parse_san(move_san)
                board.push(move)
                ply += 1
                fen = board.fen()
                if is_endgame(fen):
                    return EndgameEntry(fen=fen, ply=ply)
            except (chess.InvalidMoveError, chess.AmbiguousMoveError):
                break

        return None
