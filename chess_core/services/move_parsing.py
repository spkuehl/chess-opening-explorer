"""Shared move parsing for chess services."""


def parse_san_moves(moves: str) -> list[str]:
    """Parse a move string into individual SAN moves.

    Args:
        moves: A move string like "1. e4 e5 2. Nf3 Nc6" or "e4 e5 Nf3 Nc6".

    Returns:
        A list of SAN moves like ["e4", "e5", "Nf3", "Nc6"].
    """
    tokens = moves.split()
    san_moves = []
    for token in tokens:
        if token.endswith(".") or token.replace(".", "").isdigit():
            continue
        if token in ("1-0", "0-1", "1/2-1/2", "*"):
            continue
        san_moves.append(token)
    return san_moves
