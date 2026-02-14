"""Management command to backfill endgame_move_ply and endgame_fen for existing games."""

import time

from django.core.management.base import BaseCommand
from django.db.models import Q, QuerySet

from chess_core.models import Game
from chess_core.services import EndgameDetector


class Command(BaseCommand):
    """Backfill endgame_move_ply and endgame_fen for existing games in the database."""

    help = (
        "Detect and set endgame_move_ply and endgame_fen for existing games "
        "in the database"
    )

    def add_arguments(self, parser):
        """Add command arguments."""
        parser.add_argument(
            "--batch-size",
            type=int,
            default=1000,
            help="Number of games to process per batch (default: 1000)",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Re-detect endgame even if already set",
        )

    def handle(self, *args, **options):
        """Execute the backfill command."""
        batch_size = options["batch_size"]
        force = options["force"]

        queryset: QuerySet[Game]
        if force:
            queryset = Game.objects.all()
            self.stdout.write("Processing all games (--force mode)")
        else:
            queryset = Game.objects.filter(
                Q(endgame_move_ply__isnull=True) | Q(endgame_fen__isnull=True) | Q(endgame_fen="")
            )
            self.stdout.write("Processing games without endgame_move_ply or endgame_fen")

        total_games = queryset.count()
        if total_games == 0:
            self.stdout.write(self.style.SUCCESS("No games to process"))
            return

        self.stdout.write(f"Found {total_games} games to process")
        self.stdout.write(f"Batch size: {batch_size}")
        self.stdout.write("")

        detector = EndgameDetector()
        start_time = time.time()
        processed = 0
        updated = 0

        game_ids = list(queryset.values_list("id", flat=True))

        for i in range(0, len(game_ids), batch_size):
            batch_ids = game_ids[i : i + batch_size]
            batch = list(Game.objects.filter(id__in=batch_ids))
            games_to_update = []

            for game in batch:
                entry = detector.detect_endgame(game.moves)
                if entry is not None:
                    game.endgame_move_ply = entry.ply
                    game.endgame_fen = entry.fen[:100] if len(entry.fen) > 100 else entry.fen
                    games_to_update.append(game)

                processed += 1

            if games_to_update:
                Game.objects.bulk_update(
                    games_to_update,
                    ["endgame_move_ply", "endgame_fen"],
                )
                updated += len(games_to_update)

            self.stdout.write(
                f"Processed {processed}/{total_games} games, "
                f"updated {updated} with endgame data"
            )

        elapsed = time.time() - start_time

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(f"Completed in {elapsed:.2f} seconds"))
        self.stdout.write(self.style.SUCCESS(f"Games processed: {processed}"))
        self.stdout.write(self.style.SUCCESS(f"Games updated: {updated}"))

        with_endgame = Game.objects.filter(endgame_move_ply__isnull=False).count()
        without_endgame = Game.objects.filter(endgame_move_ply__isnull=True).count()
        self.stdout.write("")
        self.stdout.write(f"Games with endgame data: {with_endgame}")
        self.stdout.write(f"Games without endgame data: {without_endgame}")
