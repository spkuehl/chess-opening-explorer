"""Management command to import chess games from various file formats."""

import time
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from chess_core.parsers import PGNParser
from chess_core.repositories import GameRepository

FORMAT_GLOB: dict[str, str] = {"pgn": "*.pgn"}


class Command(BaseCommand):
    """Import chess games from a file or directory into the database."""

    help = (
        "Import chess games from a file or directory (PGN or other supported formats)"
    )

    def add_arguments(self, parser):
        """Add command arguments."""
        parser.add_argument(
            "path",
            type=str,
            help="Path to a game file or directory of game files to import",
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
        path = Path(options["path"])
        file_format = options["format"]
        batch_size = options["batch_size"]

        if not path.exists():
            raise CommandError(f"Path not found: {path}")

        if path.is_file():
            files_to_import = [path]
        else:
            if not path.is_dir():
                raise CommandError(f"Path is not a file or directory: {path}")
            glob = FORMAT_GLOB.get(file_format, f"*.{file_format}")
            files_to_import = sorted(path.glob(glob))
            if not files_to_import:
                raise CommandError(f"No {glob} files found in directory: {path}")

        parser = self._get_parser(file_format)
        if parser is None:
            raise CommandError(f"Unsupported format: {file_format}")

        repo = GameRepository()
        initial_count = repo.count()

        self.stdout.write(f"Importing from: {path} ({len(files_to_import)} file(s))")
        self.stdout.write(f"Format: {file_format}")
        self.stdout.write(f"Batch size: {batch_size}")
        self.stdout.write("")

        start_time = time.time()
        total_processed = 0

        for file_path in files_to_import:
            self.stdout.write(f"  {file_path.name}...")
            games = parser.parse(file_path)
            total_processed += repo.save_batch(games, batch_size=batch_size)

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
        if file_format == "pgn":
            return PGNParser()
        return None
