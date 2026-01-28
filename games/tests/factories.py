"""Factory classes for creating test data."""

import factory
from factory.django import DjangoModelFactory

from games.models import Game, Opening


class OpeningFactory(DjangoModelFactory):
    """Factory for creating Opening instances."""

    class Meta:
        model = Opening

    fen = factory.Sequence(
        lambda n: f"rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 {n}"
    )
    eco_code = factory.Sequence(lambda n: f"A{n:02d}")
    name = factory.Sequence(lambda n: f"Test Opening {n}")
    moves = factory.Sequence(lambda n: f"1. e{n % 4 + 1}")
    ply_count = 1
    source = "test"
    is_eco_root = False


class GameFactory(DjangoModelFactory):
    """Factory for creating Game instances."""

    class Meta:
        model = Game

    source_id = factory.Sequence(lambda n: f"game_{n:08d}")
    event = factory.Sequence(lambda n: f"Test Event {n}")
    site = "Test Site"
    date = factory.LazyFunction(lambda: None)
    round = "1"
    white_player = factory.Sequence(lambda n: f"White Player {n}")
    black_player = factory.Sequence(lambda n: f"Black Player {n}")
    result = "1-0"
    white_elo = 2500
    black_elo = 2400
    time_control = "300+0"
    termination = "Normal"
    moves = "1. e4 e5 2. Nf3 Nc6"
    source_format = "pgn"
    raw_headers = factory.LazyFunction(dict)
    opening = None
