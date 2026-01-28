"""Django models for chess games."""

from django.db import models


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
    white_elo = models.IntegerField(null=True, blank=True)
    black_elo = models.IntegerField(null=True, blank=True)
    time_control = models.CharField(max_length=50, blank=True)
    termination = models.TextField(blank=True)
    moves = models.TextField()
    source_format = models.CharField(max_length=50)
    raw_headers = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["event"]),
        ]

    def __str__(self) -> str:
        """Return a string representation of the game."""
        return f"{self.white_player} vs {self.black_player} ({self.date})"
