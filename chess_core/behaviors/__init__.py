"""Chess position behaviors (e.g. endgame detection from FEN)."""

from .endgame import ENDGAME_THRESHOLD, is_endgame

__all__ = ["ENDGAME_THRESHOLD", "is_endgame"]
