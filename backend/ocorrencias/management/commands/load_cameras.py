"""Load `cameras_areas_fm.csv` into the Camera table.

Usage:
    python manage.py load_cameras <path/to/csv> [--truncate]
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from django.contrib.gis.geos import GEOSGeometry
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from ocorrencias.models import Camera

from ._helpers import safe_int, safe_str

CHUNK_SIZE = 1_000
BATCH_SIZE = 500


class Command(BaseCommand):
    help = "Load cameras_areas_fm CSV into the Camera table."

    def add_arguments(self, parser) -> None:
        parser.add_argument("csv_path", type=str)
        parser.add_argument("--truncate", action="store_true")
        parser.add_argument("--limit", type=int, default=None)

    def handle(self, *args, **opts) -> None:
        path = Path(opts["csv_path"]).expanduser().resolve()
        if not path.exists():
            raise CommandError(f"CSV not found: {path}")

        if opts["truncate"]:
            n = Camera.objects.count()
            Camera.objects.all().delete()
            self.stdout.write(self.style.WARNING(f"Truncated {n} existing rows."))

        stats = {"read": 0, "imported": 0, "skipped_no_geom": 0, "skipped_no_id": 0}
        limit = opts["limit"]

        reader = pd.read_csv(path, chunksize=CHUNK_SIZE, dtype=str, keep_default_na=False)

        for chunk_idx, chunk in enumerate(reader):
            objs: list[Camera] = []
            for _, row in chunk.iterrows():
                stats["read"] += 1

                pk = safe_str(row.get("id_ponto"), 36)
                if not pk:
                    stats["skipped_no_id"] += 1
                    continue

                wkt = safe_str(row.get("geometry"))
                if not wkt:
                    stats["skipped_no_geom"] += 1
                    continue
                try:
                    geom = GEOSGeometry(wkt, srid=4326)
                except Exception:
                    stats["skipped_no_geom"] += 1
                    continue

                id_trecho = safe_int(row.get("id_trecho")) or 0

                objs.append(
                    Camera(
                        id_ponto=pk,
                        nome_area_fm=safe_str(row.get("nome_area_fm"), 120),
                        id_trecho=id_trecho,
                        location=geom,
                    )
                )

                if limit is not None and stats["read"] >= limit:
                    break

            if objs:
                with transaction.atomic():
                    Camera.objects.bulk_create(
                        objs, batch_size=BATCH_SIZE, ignore_conflicts=True
                    )
                stats["imported"] += len(objs)

            self.stdout.write(
                f"chunk {chunk_idx + 1}: read={stats['read']} imported={stats['imported']}"
            )

            if limit is not None and stats["read"] >= limit:
                break

        self.stdout.write(self.style.SUCCESS("Load complete."))
        for k, v in stats.items():
            self.stdout.write(f"  {k:20s}: {v}")
        self.stdout.write(f"  rows in db          : {Camera.objects.count()}")
