"""Load every source CSV into the database in a single command.

Usage:
    python manage.py load_data
    python manage.py load_data --truncate
    python manage.py load_data --only cameras,ocorrencias
    python manage.py load_data --data-dir /custom/path --limit 5000
"""

from __future__ import annotations

from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from ocorrencias.loaders import DATASETS


class Command(BaseCommand):
    help = "Load every source CSV (ocorrencias, cameras, disk_denuncia, fatores_urbanos)."

    def add_arguments(self, parser) -> None:
        default_dir = Path(settings.REPO_DIR) / "data"
        parser.add_argument(
            "--data-dir",
            type=str,
            default=str(default_dir),
            help="Directory containing the CSVs (default: <repo>/data).",
        )
        parser.add_argument(
            "--truncate",
            action="store_true",
            help="Delete existing rows in each selected table before loading.",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=None,
            help="Per-dataset row limit (debug). Applies to every loader.",
        )
        parser.add_argument(
            "--only",
            type=str,
            default=None,
            help=f"Comma-separated subset. Available: {','.join(DATASETS)}",
        )

    def handle(self, *args, **opts) -> None:
        data_dir = Path(opts["data_dir"]).expanduser().resolve()
        if not data_dir.is_dir():
            raise CommandError(f"--data-dir is not a directory: {data_dir}")

        if opts["only"]:
            requested = {k.strip() for k in opts["only"].split(",") if k.strip()}
            unknown = requested - DATASETS.keys()
            if unknown:
                raise CommandError(
                    f"unknown dataset(s): {sorted(unknown)}; available: {sorted(DATASETS)}"
                )
        else:
            requested = set(DATASETS)

        summary: dict[str, dict[str, int]] = {}
        for key, (filename, loader) in DATASETS.items():
            if key not in requested:
                continue
            path = data_dir / filename
            self.stdout.write(self.style.HTTP_INFO(f"\n→ {key}  ({filename})"))
            if not path.exists():
                self.stdout.write(self.style.WARNING(f"  missing, skipped: {path}"))
                continue
            stats = loader(
                path,
                truncate=opts["truncate"],
                limit=opts["limit"],
                report=lambda msg: self.stdout.write(msg),
            )
            summary[key] = stats
            for k, v in stats.items():
                self.stdout.write(f"    {k:18s}: {v}")

        if not summary:
            self.stdout.write(self.style.WARNING("\nNo datasets were loaded."))
            return

        self.stdout.write(self.style.SUCCESS("\n== Load complete =="))
        for key, stats in summary.items():
            self.stdout.write(
                f"  {key:18s}: imported={stats.get('imported', 0):>6}  "
                f"rows_in_db={stats.get('rows_in_db', '-')}"
            )
