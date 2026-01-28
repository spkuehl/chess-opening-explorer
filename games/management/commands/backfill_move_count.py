"""Management command to backfill move_count_ply for existing games."""

import time

from django.core.management.base import BaseCommand
from django.db.models import QuerySet

from games.models import Game


class Command(BaseCommand):
    """Backfill move_count_ply for existing games in the database."""

    help = "Calculate and set move_count_ply for existing games in the database"

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
            help="Re-calculate move_count_ply even if already set",
        )

    def handle(self, *args, **options):
        """Execute the backfill command."""
        batch_size = options["batch_size"]
        force = options["force"]

        # Get games to process
        queryset: QuerySet[Game]
        if force:
            queryset = Game.objects.all()
            self.stdout.write("Processing all games (--force mode)")
        else:
            queryset = Game.objects.filter(move_count_ply__isnull=True)
            self.stdout.write("Processing games without move_count_ply")

        total_games = queryset.count()
        if total_games == 0:
            self.stdout.write(self.style.SUCCESS("No games to process"))
            return

        self.stdout.write(f"Found {total_games} games to process")
        self.stdout.write(f"Batch size: {batch_size}")
        self.stdout.write("")

        start_time = time.time()
        processed = 0
        updated = 0

        # Get all game IDs to process (to avoid queryset changes during iteration)
        game_ids = list(queryset.values_list("id", flat=True))

        # Process in batches
        for i in range(0, len(game_ids), batch_size):
            batch_ids = game_ids[i : i + batch_size]
            batch = list(Game.objects.filter(id__in=batch_ids))

            games_to_update = []

            for game in batch:
                move_count_ply = self._count_moves(game.moves)
                if move_count_ply is not None:
                    game.move_count_ply = move_count_ply
                    games_to_update.append(game)

                processed += 1

            # Bulk update the batch
            if games_to_update:
                Game.objects.bulk_update(
                    games_to_update,
                    ["move_count_ply"],
                )
                updated += len(games_to_update)

            self.stdout.write(
                f"Processed {processed}/{total_games} games, "
                f"updated {updated} with move_count_ply"
            )

        elapsed = time.time() - start_time

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(f"Completed in {elapsed:.2f} seconds"))
        self.stdout.write(self.style.SUCCESS(f"Games processed: {processed}"))
        self.stdout.write(self.style.SUCCESS(f"Games updated: {updated}"))

        # Show summary stats
        total_with_count = Game.objects.filter(move_count_ply__isnull=False).count()
        total_without_count = Game.objects.filter(move_count_ply__isnull=True).count()
        self.stdout.write("")
        self.stdout.write(f"Games with move_count_ply: {total_with_count}")
        self.stdout.write(f"Games without move_count_ply: {total_without_count}")

    def _count_moves(self, moves: str) -> int | None:
        """Count the number of half-moves (ply) in a move string.

        Args:
            moves: A move string in SAN format, e.g., "1. e4 e5 2. Nf3 Nc6".

        Returns:
            The number of half-moves (ply), or None if moves is empty.
        """
        if not moves:
            return None

        tokens = moves.split()
        move_count = 0

        for token in tokens:
            # Skip move numbers (e.g., "1.", "2.", "1...")
            if token.endswith(".") or token.replace(".", "").isdigit():
                continue
            # Skip result markers
            if token in ("1-0", "0-1", "1/2-1/2", "*"):
                continue
            move_count += 1

        return move_count if move_count > 0 else None
