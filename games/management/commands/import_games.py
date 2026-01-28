"""Management command to import chess games from various file formats."""

import time
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from games.parsers import PGNParser
from games.repositories import GameRepository


class Command(BaseCommand):
    """Import chess games from a file into the database."""

    help = "Import chess games from a file (PGN or other supported formats)"

    def add_arguments(self, parser):
        """Add command arguments."""
        parser.add_argument(
            "file",
            type=str,
            help="Path to the game file to import",
        )
        parser.add_argument(
            "--format",
            type=str,
            default="pgn",
            choices=["pgn"],
            help="File format (default: pgn)",
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=1000,
            help="Number of games to insert per batch (default: 1000)",
        )

    def handle(self, *args, **options):
        """Execute the import command."""
        file_path = Path(options["file"])
        file_format = options["format"]
        batch_size = options["batch_size"]

        # Validate file exists
        if not file_path.exists():
            raise CommandError(f"File not found: {file_path}")

        # Select parser based on format
        parser = self._get_parser(file_format)
        if parser is None:
            raise CommandError(f"Unsupported format: {file_format}")

        repo = GameRepository()

        # Get initial count
        initial_count = repo.count()

        self.stdout.write(f"Importing games from: {file_path}")
        self.stdout.write(f"Format: {file_format}")
        self.stdout.write(f"Batch size: {batch_size}")
        self.stdout.write("")

        start_time = time.time()

        # Parse and save games
        games = parser.parse(file_path)
        total_processed = repo.save_batch(games, batch_size=batch_size)

        elapsed = time.time() - start_time
        final_count = repo.count()
        new_games = final_count - initial_count

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                f"Processed {total_processed} games in {elapsed:.2f} seconds"
            )
        )
        self.stdout.write(self.style.SUCCESS(f"New games added: {new_games}"))
        self.stdout.write(self.style.SUCCESS(f"Total games in database: {final_count}"))

    def _get_parser(self, file_format: str):
        """Get the appropriate parser for the file format.

        Args:
            file_format: The format string (e.g., "pgn").

        Returns:
            A parser instance or None if format is unsupported.
        """
        parsers = {
            "pgn": PGNParser,
        }
        parser_class = parsers.get(file_format)
        if parser_class:
            return parser_class()
        return None
