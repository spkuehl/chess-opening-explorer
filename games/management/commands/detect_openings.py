"""Management command to detect openings for existing games."""

import time

from django.core.management.base import BaseCommand
from django.db.models import QuerySet

from games.models import Game, Opening
from games.services.openings import OpeningDetector


class Command(BaseCommand):
    """Detect openings for existing games in the database."""

    help = "Detect and assign openings to existing games in the database"

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
            help="Re-detect openings even if already set",
        )

    def handle(self, *args, **options):
        """Execute the detect command."""
        batch_size = options["batch_size"]
        force = options["force"]

        # Initialize detector
        self.stdout.write("Loading opening database...")
        detector = OpeningDetector()
        self.stdout.write(f"Loaded {len(detector._fen_set)} opening positions")

        # Build FEN → Opening ID cache
        fen_to_opening_id: dict[str, int] = dict(
            Opening.objects.values_list("fen", "id")
        )

        # Get games to process
        queryset: QuerySet[Game]
        if force:
            queryset = Game.objects.all()
            self.stdout.write("Processing all games (--force mode)")
        else:
            queryset = Game.objects.filter(opening__isnull=True)
            self.stdout.write("Processing games without openings")

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
                match = detector.detect_opening(game.moves)
                if match:
                    opening_id = fen_to_opening_id.get(match.fen)
                    if opening_id:
                        game.opening_id = opening_id
                        games_to_update.append(game)

                processed += 1

            # Bulk update the batch
            if games_to_update:
                Game.objects.bulk_update(
                    games_to_update,
                    ["opening_id"],
                )
                updated += len(games_to_update)

            self.stdout.write(
                f"Processed {processed}/{total_games} games, "
                f"updated {updated} with openings"
            )

        elapsed = time.time() - start_time

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(f"Completed in {elapsed:.2f} seconds"))
        self.stdout.write(self.style.SUCCESS(f"Games processed: {processed}"))
        self.stdout.write(self.style.SUCCESS(f"Games updated with openings: {updated}"))

        # Show summary stats
        total_with_opening = Game.objects.filter(opening__isnull=False).count()
        total_without_opening = Game.objects.filter(opening__isnull=True).count()
        self.stdout.write("")
        self.stdout.write(f"Games with openings: {total_with_opening}")
        self.stdout.write(f"Games without openings: {total_without_opening}")
