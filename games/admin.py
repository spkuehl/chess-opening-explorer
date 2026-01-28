"""Django admin configuration for chess games."""

from django.contrib import admin

from .models import Game


@admin.register(Game)
class GameAdmin(admin.ModelAdmin):
    """Admin interface for Game model."""

    list_display = [
        "id",
        "white_player",
        "black_player",
        "result",
        "event",
        "date",
        "white_elo",
        "black_elo",
    ]
    list_display_links = ["id"]
    list_filter = ["event", "result", "source_format", "date"]
    search_fields = ["white_player", "black_player", "event"]
    date_hierarchy = "date"
    readonly_fields = ["source_id", "created_at"]
