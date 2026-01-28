"""Chess game parsers package.

This package provides parsers for various chess game formats.
All parsers implement the GameParser protocol and produce GameData objects.
"""

from .base import GameData, GameParser
from .pgn import PGNParser

__all__ = ["GameData", "GameParser", "PGNParser"]
