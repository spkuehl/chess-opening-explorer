"""Django models for chess games."""

from django.db import models


class Opening(models.Model):
    """Represents a chess opening from ECO classification.

    ECO (Encyclopedia of Chess Openings) data is loaded from JSON files.
    Each opening is identified by a unique FEN position string.
    """

    fen = models.CharField(max_length=100, unique=True, db_index=True)
    eco_code = models.CharField(max_length=10, db_index=True)
    name = models.CharField(max_length=255, db_index=True)
    moves = models.CharField(max_length=500)
    ply_count = models.IntegerField()
    source = models.CharField(max_length=50, blank=True)
    is_eco_root = models.BooleanField(default=False)

    class Meta:
        db_table = "opening"
        indexes = [
            models.Index(fields=["eco_code"]),
            models.Index(fields=["name"]),
        ]

    def __str__(self) -> str:
        """Return a string representation of the opening."""
        return f"{self.eco_code}: {self.name}"


class Game(models.Model):
    """Represents a chess game with metadata and moves."""

    source_id = models.CharField(max_length=64, unique=True, db_index=True)
    event = models.CharField(max_length=255, blank=True)
    site = models.CharField(max_length=255, blank=True)
    date = models.DateField(null=True, blank=True, db_index=True)
    round = models.CharField(max_length=50, blank=True)
    white_player = models.CharField(max_length=255, db_index=True)
    black_player = models.CharField(max_length=255, db_index=True)
    result = models.CharField(max_length=10)
    white_elo = models.IntegerField(null=True, blank=True, db_index=True)
    black_elo = models.IntegerField(null=True, blank=True, db_index=True)
    time_control = models.CharField(max_length=50, blank=True)
    termination = models.TextField(blank=True)
    moves = models.TextField()
    source_format = models.CharField(max_length=50)
    raw_headers = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    move_count_ply = models.IntegerField(null=True, blank=True, db_index=True)
    opening = models.ForeignKey(
        Opening, null=True, blank=True, on_delete=models.SET_NULL, db_index=True
    )

    class Meta:
        db_table = "game"
        indexes = [
            models.Index(fields=["event"]),
        ]

    def __str__(self) -> str:
        """Return a string representation of the game."""
        return f"{self.white_player} vs {self.black_player} ({self.date})"
