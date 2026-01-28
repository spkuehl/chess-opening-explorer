"""Django admin configuration for chess games."""

from django.contrib import admin

from .models import Game, Opening


@admin.register(Opening)
class OpeningAdmin(admin.ModelAdmin):
    """Admin interface for Opening model."""

    list_display = ["id", "eco_code", "name", "ply_count", "is_eco_root"]
    list_display_links = ["id"]
    list_filter = ["eco_code", "is_eco_root", "source"]
    search_fields = ["eco_code", "name", "moves"]
    ordering = ["eco_code", "ply_count"]


@admin.register(Game)
class GameAdmin(admin.ModelAdmin):
    """Admin interface for Game model."""

    list_display = [
        "id",
        "white_player",
        "black_player",
        "result",
        "opening",
        "event",
        "date",
        "white_elo",
        "black_elo",
    ]
    list_display_links = ["id"]
    list_filter = ["event", "result", "source_format", "date", "opening"]
    search_fields = ["white_player", "black_player", "event"]
    date_hierarchy = "date"
    readonly_fields = ["source_id", "created_at"]
