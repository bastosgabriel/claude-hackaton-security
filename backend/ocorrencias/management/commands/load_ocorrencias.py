"""Load `df_ocorrencias_tratado` CSV into the Ocorrencia table.

Usage:
    python manage.py load_ocorrencias <path/to/csv> [--truncate]
"""

from __future__ import annotations

import datetime as dt
import math
from pathlib import Path

import pandas as pd
from django.contrib.gis.geos import Point
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from ocorrencias.models import Ocorrencia

CHUNK_SIZE = 10_000
BATCH_SIZE = 2_000
YEAR_MIN = 2000
YEAR_MAX = dt.date.today().year + 1


def parse_data(raw: object, ano: int | None) -> dt.date | None:
    """Parse DD/MM/YYYY; reject if year doesn't match `ano` or is out of range."""
    if raw is None or (isinstance(raw, float) and math.isnan(raw)):
        return None
    s = str(raw).strip()
    if not s:
        return None
    try:
        parsed = dt.datetime.strptime(s, "%d/%m/%Y").date()
    except ValueError:
        return None
    if not (YEAR_MIN <= parsed.year <= YEAR_MAX):
        return None
    if ano is not None and parsed.year != ano:
        return None
    return parsed


def parse_hora(raw: object) -> dt.time | None:
    if raw is None or (isinstance(raw, float) and math.isnan(raw)):
        return None
    s = str(raw).strip()
    if not s:
        return None
    for fmt in ("%H:%M:%S", "%H:%M"):
        try:
            return dt.datetime.strptime(s, fmt).time()
        except ValueError:
            continue
    return None


def safe_int(raw: object) -> int | None:
    if raw is None or (isinstance(raw, float) and math.isnan(raw)):
        return None
    try:
        return int(float(raw))
    except (TypeError, ValueError):
        return None


def safe_str(raw: object, max_len: int | None = None) -> str:
    if raw is None or (isinstance(raw, float) and math.isnan(raw)):
        return ""
    s = str(raw).strip()
    return s[:max_len] if max_len else s


def safe_coord(raw: object) -> float | None:
    if raw is None or (isinstance(raw, float) and math.isnan(raw)):
        return None
    try:
        v = float(raw)
    except (TypeError, ValueError):
        return None
    if v == 0.0:
        return None
    return v


class Command(BaseCommand):
    help = "Load the df_ocorrencias_tratado CSV into the Ocorrencia table."

    def add_arguments(self, parser) -> None:
        parser.add_argument("csv_path", type=str, help="Path to the CSV file")
        parser.add_argument(
            "--truncate",
            action="store_true",
            help="Delete all existing Ocorrencia rows before loading.",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=None,
            help="Stop after loading this many rows (debug).",
        )

    def handle(self, *args, **opts) -> None:
        path = Path(opts["csv_path"]).expanduser().resolve()
        if not path.exists():
            raise CommandError(f"CSV not found: {path}")

        if opts["truncate"]:
            n = Ocorrencia.objects.count()
            Ocorrencia.objects.all().delete()
            self.stdout.write(self.style.WARNING(f"Truncated {n} existing rows."))

        stats = {"read": 0, "imported": 0, "skipped_no_coord": 0, "skipped_no_id": 0, "date_nulled": 0}
        limit = opts["limit"]

        reader = pd.read_csv(
            path,
            chunksize=CHUNK_SIZE,
            dtype=str,
            keep_default_na=True,
            na_values=["", "nan", "NaN"],
        )

        for chunk_idx, chunk in enumerate(reader):
            objs: list[Ocorrencia] = []
            for _, row in chunk.iterrows():
                stats["read"] += 1

                pk = safe_str(row.get("id_criptografado"), 64)
                if not pk:
                    stats["skipped_no_id"] += 1
                    continue

                lat = safe_coord(row.get("latitude"))
                lon = safe_coord(row.get("longitude"))
                if lat is None or lon is None:
                    stats["skipped_no_coord"] += 1
                    continue

                ano = safe_int(row.get("ano"))
                data = parse_data(row.get("data"), ano)
                if data is None and row.get("data"):
                    stats["date_nulled"] += 1

                objs.append(
                    Ocorrencia(
                        id_criptografado=pk,
                        ano=ano if ano is not None else 0,
                        mes=safe_int(row.get("mes")) or 0,
                        data=data,
                        hora=parse_hora(row.get("hora")),
                        delito=safe_int(row.get("delito")),
                        desc_delito=safe_str(row.get("desc_delito"), 120),
                        aisp=safe_int(row.get("aisp")),
                        risp=safe_int(row.get("risp")),
                        locf=safe_str(row.get("locf"), 255),
                        dia_semana=safe_str(row.get("dia_semana"), 20),
                        location=Point(lon, lat, srid=4326),
                    )
                )

                if limit is not None and stats["read"] >= limit:
                    break

            if objs:
                with transaction.atomic():
                    Ocorrencia.objects.bulk_create(
                        objs,
                        batch_size=BATCH_SIZE,
                        ignore_conflicts=True,
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
        self.stdout.write(f"  rows in db          : {Ocorrencia.objects.count()}")
