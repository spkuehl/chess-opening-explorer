"""Management command to load ECO opening data from JSON files."""

import json
import time
from pathlib import Path

from django.core.management.base import BaseCommand

from chess_core.models import Opening


class Command(BaseCommand):
    """Load ECO opening data from JSON files into the Opening table."""

    help = "Load ECO opening data from JSON files into the database"

    def add_arguments(self, parser):
        """Add command arguments."""
        parser.add_argument(
            "--data-dir",
            type=str,
            default=None,
            help="Path to directory containing ECO JSON files (default: games/data/)",
        )
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Clear existing openings before loading",
        )

    def handle(self, *args, **options):
        """Execute the load command."""
        data_dir = options["data_dir"]
        if data_dir:
            data_path = Path(data_dir)
        else:
            data_path = Path(__file__).parent.parent.parent / "data"

        if not data_path.exists():
            self.stderr.write(
                self.style.ERROR(f"Data directory not found: {data_path}")
            )
            return

        files = [
            "ecoA.json",
            "ecoB.json",
            "ecoC.json",
            "ecoD.json",
            "ecoE.json",
            "eco_interpolated.json",
        ]

        # Check all files exist
        missing_files = [f for f in files if not (data_path / f).exists()]
        if missing_files:
            self.stderr.write(
                self.style.ERROR(f"Missing files: {', '.join(missing_files)}")
            )
            return

        if options["clear"]:
            self.stdout.write("Clearing existing openings...")
            deleted_count, _ = Opening.objects.all().delete()
            self.stdout.write(f"Deleted {deleted_count} openings")

        self.stdout.write(f"Loading openings from: {data_path}")
        self.stdout.write("")

        start_time = time.time()
        total_loaded = 0
        total_skipped = 0

        for filename in files:
            file_path = data_path / filename
            self.stdout.write(f"Processing {filename}...")

            with open(file_path, encoding="utf-8") as f:
                data = json.load(f)

            openings = []
            for fen, info in data.items():
                openings.append(
                    Opening(
                        fen=fen,
                        eco_code=info["eco"],
                        name=info["name"],
                        moves=info["moves"],
                        ply_count=self._count_plies(info["moves"]),
                        source=info.get("src", ""),
                        is_eco_root=info.get("isEcoRoot", False),
                    )
                )

            # Use bulk_create with ignore_conflicts to handle duplicates
            created = Opening.objects.bulk_create(openings, ignore_conflicts=True)
            file_loaded = len(created)
            file_skipped = len(openings) - file_loaded

            total_loaded += file_loaded
            total_skipped += file_skipped

            self.stdout.write(
                f"  Loaded: {file_loaded}, Skipped (duplicates): {file_skipped}"
            )

        elapsed = time.time() - start_time
        final_count = Opening.objects.count()

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(f"Completed in {elapsed:.2f} seconds"))
        self.stdout.write(self.style.SUCCESS(f"New openings loaded: {total_loaded}"))
        self.stdout.write(self.style.SUCCESS(f"Skipped (duplicates): {total_skipped}"))
        self.stdout.write(
            self.style.SUCCESS(f"Total openings in database: {final_count}")
        )

    def _count_plies(self, moves: str) -> int:
        """Count the number of plies (half-moves) in a move string.

        Args:
            moves: A move string like "1. e4 e5 2. Nf3 Nc6"

        Returns:
            The number of plies (individual moves by each player).
        """
        if not moves:
            return 0

        # Split by whitespace and filter out move numbers (like "1.", "2.")
        tokens = moves.split()
        ply_count = 0
        for token in tokens:
            # Skip move numbers (end with . like "1." or "2.")
            if not token.endswith("."):
                ply_count += 1

        return ply_count
