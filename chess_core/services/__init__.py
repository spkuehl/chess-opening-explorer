"""Services for chess game analysis."""

from chess_core.services.endgame import EndgameDetector, EndgameEntry
from chess_core.services.openings import OpeningDetector, OpeningMatch

__all__ = [
    "EndgameDetector",
    "EndgameEntry",
    "OpeningDetector",
    "OpeningMatch",
]
