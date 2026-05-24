"""Load `disk_denuncia.csv` into the DiskDenuncia table.

Notes on the CSV format:
  * Encoding: Latin-1 (Windows-1252-ish).
  * Delimiter: semicolon.
  * Decimal separator in latitude/longitude: comma.
  * Date format: M/D/YYYY H:MM:SS (US month-first).
  * Denormalized: 1 parent row + N child rows per complaint. We keep only
    parent rows (rows where ``numero_denuncia`` is non-empty).

Usage:
    python manage.py load_disk_denuncia <path/to/csv> [--truncate]
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from django.contrib.gis.geos import Point
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from ocorrencias.models import DiskDenuncia

from ._helpers import parse_datetime, safe_bool, safe_coord, safe_int, safe_str

CHUNK_SIZE = 5_000
BATCH_SIZE = 1_000
DATETIME_FMT = "%m/%d/%Y %H:%M:%S"


class Command(BaseCommand):
    help = "Load disk_denuncia CSV into the DiskDenuncia table."

    def add_arguments(self, parser) -> None:
        parser.add_argument("csv_path", type=str)
        parser.add_argument("--truncate", action="store_true")
        parser.add_argument("--limit", type=int, default=None)

    def handle(self, *args, **opts) -> None:
        path = Path(opts["csv_path"]).expanduser().resolve()
        if not path.exists():
            raise CommandError(f"CSV not found: {path}")

        if opts["truncate"]:
            n = DiskDenuncia.objects.count()
            DiskDenuncia.objects.all().delete()
            self.stdout.write(self.style.WARNING(f"Truncated {n} existing rows."))

        stats = {
            "read": 0,
            "parents": 0,
            "imported": 0,
            "skipped_child": 0,
            "skipped_no_id": 0,
            "skipped_no_coord": 0,
        }
        limit = opts["limit"]

        reader = pd.read_csv(
            path,
            chunksize=CHUNK_SIZE,
            dtype=str,
            sep=";",
            encoding="latin-1",
            keep_default_na=False,
        )

        for chunk_idx, chunk in enumerate(reader):
            objs: list[DiskDenuncia] = []
            for _, row in chunk.iterrows():
                stats["read"] += 1

                numero = safe_str(row.get("numero_denuncia"), 30)
                if not numero:
                    stats["skipped_child"] += 1
                    continue
                stats["parents"] += 1

                id_denuncia = safe_int(row.get("id_denuncia"))
                if id_denuncia is None:
                    stats["skipped_no_id"] += 1
                    continue

                lat = safe_coord(row.get("latitude"), decimal_sep=",")
                lng = safe_coord(row.get("longitude"), decimal_sep=",")
                location = (
                    Point(lng, lat, srid=4326) if lat is not None and lng is not None else None
                )
                if location is None:
                    stats["skipped_no_coord"] += 1  # still imported, just no geom

                objs.append(
                    DiskDenuncia(
                        id_denuncia=id_denuncia,
                        numero_denuncia=numero,
                        data_denuncia=parse_datetime(row.get("data_denuncia"), DATETIME_FMT),
                        data_difusao=parse_datetime(row.get("data_difusao"), DATETIME_FMT),
                        timestamp_insercao=parse_datetime(
                            row.get("timestamp_insercao"), DATETIME_FMT
                        ),
                        tipo_logradouro=safe_str(row.get("tipo_logradouro"), 10),
                        logradouro=safe_str(row.get("logradouro"), 120),
                        numero_logradouro=safe_str(row.get("numero_logradouro"), 20),
                        complemento_logradouro=safe_str(row.get("complemento_logradouro"), 120),
                        bairro_logradouro=safe_str(row.get("bairro_logradouro"), 80),
                        subbairro_logradouro=safe_str(row.get("subbairro_logradouro"), 80),
                        cep_logradouro=safe_str(row.get("cep_logradouro"), 9),
                        referencia_logradouro=safe_str(row.get("referencia_logradouro"), 255),
                        municipio=safe_str(row.get("municipio"), 80),
                        estado=safe_str(row.get("estado"), 2),
                        location=location,
                        xpto_id=safe_int(row.get("xptos.id")),
                        xpto_nome=safe_str(row.get("xptos.nome"), 80),
                        orgao_id=safe_int(row.get("orgaos.id")),
                        orgao_nome=safe_str(row.get("orgaos.nome"), 100),
                        orgao_tipo=safe_str(row.get("orgaos.tipo"), 12),
                        id_classe=safe_int(row.get("assuntos.id_classe")),
                        classe=safe_str(row.get("assuntos.classe"), 100),
                        id_tipo=safe_int(row.get("assuntos.tipos.id_tipo")),
                        tipo=safe_str(row.get("assuntos.tipos.tipo"), 100),
                        assunto_principal=_parse_assunto_principal(
                            row.get("assuntos.tipos.assunto_principal")
                        ),
                        envolvido_id=safe_int(row.get("envolvidos.id")),
                        envolvido_sexo=safe_str(row.get("envolvidos.sexo"), 1),
                        envolvido_idade=safe_int(row.get("envolvidos.idade")),
                        envolvido_pele=safe_str(row.get("envolvidos.pele"), 20),
                        envolvido_estatura=safe_str(row.get("envolvidos.estatura"), 10),
                        envolvido_porte=safe_str(row.get("envolvidos.porte"), 10),
                        envolvido_cabelos=safe_str(row.get("envolvidos.cabelos"), 40),
                        envolvido_olhos=safe_str(row.get("envolvidos.olhos"), 40),
                        envolvido_outras_caracteristicas=safe_str(
                            row.get("envolvidos.outras_caracteristicas")
                        ),
                        status_denuncia=safe_str(row.get("status_denuncia"), 40),
                        relato_redacted=safe_str(row.get("relato_redacted")),
                    )
                )

                if limit is not None and stats["parents"] >= limit:
                    break

            if objs:
                with transaction.atomic():
                    DiskDenuncia.objects.bulk_create(
                        objs, batch_size=BATCH_SIZE, ignore_conflicts=True
                    )
                stats["imported"] += len(objs)

            self.stdout.write(
                f"chunk {chunk_idx + 1}: read={stats['read']} parents={stats['parents']} "
                f"imported={stats['imported']}"
            )

            if limit is not None and stats["parents"] >= limit:
                break

        self.stdout.write(self.style.SUCCESS("Load complete."))
        for k, v in stats.items():
            self.stdout.write(f"  {k:20s}: {v}")
        self.stdout.write(f"  rows in db          : {DiskDenuncia.objects.count()}")


def _parse_assunto_principal(raw: object) -> bool | None:
    """CSV stores 0/1 ints, not TRUE/FALSE — handle both."""
    i = safe_int(raw)
    if i is not None:
        return bool(i)
    return safe_bool(raw)
