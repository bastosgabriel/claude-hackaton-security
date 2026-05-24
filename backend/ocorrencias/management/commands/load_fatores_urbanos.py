"""Load `fatores_urbanos.csv` into the FatorUrbano table.

Notes on the CSV format:
  * Multi-line records (HTML breaks in ``ocorrencia_informacao``) — relies on
    pandas' default RFC 4180 quoting, so we read with the default engine.
  * ``coordenada_x`` is latitude; ``coordenada_y`` is longitude (inverted
    naming). We pass them to ``Point(lng, lat)`` accordingly.

Usage:
    python manage.py load_fatores_urbanos <path/to/csv> [--truncate]
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from django.contrib.gis.geos import Point
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from ocorrencias.models import FatorUrbano

from ._helpers import safe_bool, safe_coord, safe_int, safe_str

CHUNK_SIZE = 2_000
BATCH_SIZE = 500


class Command(BaseCommand):
    help = "Load fatores_urbanos CSV into the FatorUrbano table."

    def add_arguments(self, parser) -> None:
        parser.add_argument("csv_path", type=str)
        parser.add_argument("--truncate", action="store_true")
        parser.add_argument("--limit", type=int, default=None)

    def handle(self, *args, **opts) -> None:
        path = Path(opts["csv_path"]).expanduser().resolve()
        if not path.exists():
            raise CommandError(f"CSV not found: {path}")

        if opts["truncate"]:
            n = FatorUrbano.objects.count()
            FatorUrbano.objects.all().delete()
            self.stdout.write(self.style.WARNING(f"Truncated {n} existing rows."))

        stats = {"read": 0, "imported": 0, "skipped_no_id": 0, "skipped_no_coord": 0}
        limit = opts["limit"]

        reader = pd.read_csv(path, chunksize=CHUNK_SIZE, dtype=str, keep_default_na=False)

        for chunk_idx, chunk in enumerate(reader):
            objs: list[FatorUrbano] = []
            for _, row in chunk.iterrows():
                stats["read"] += 1

                pk = safe_int(row.get("id_resposta_ocorrencia"))
                if pk is None:
                    stats["skipped_no_id"] += 1
                    continue

                lat = safe_coord(row.get("coordenada_x"))  # column inversion: x=lat
                lng = safe_coord(row.get("coordenada_y"))  # y=lng
                if lat is None or lng is None:
                    stats["skipped_no_coord"] += 1
                    continue

                id_tipo = safe_int(row.get("id_tipo_ocorrencia"))
                if id_tipo is None:
                    # Category is required (NOT NULL on the model).
                    stats["skipped_no_id"] += 1
                    continue

                objs.append(
                    FatorUrbano(
                        id_resposta_ocorrencia=pk,
                        logradouro=safe_str(row.get("logradouro"), 255),
                        numero_porta=safe_str(row.get("numero_porta"), 64),
                        referencia=safe_str(row.get("referencia"), 512),
                        observacao=safe_str(row.get("observacao")),
                        location=Point(lng, lat, srid=4326),
                        endereco_informado=safe_bool(row.get("endereco_informado")),
                        valido=safe_bool(row.get("valido")),
                        id_bairro=safe_int(row.get("id_bairro")),
                        bairro_nome=safe_str(row.get("bairro_nome"), 120),
                        id_subarea=safe_int(row.get("id_subarea")),
                        subarea_nome=safe_str(row.get("subarea_nome"), 255),
                        id_tipo_ocorrencia=id_tipo,
                        tipo_ocorrencia_descricao=safe_str(
                            row.get("tipo_ocorrencia_descricao"), 255
                        ),
                        tipo_ocorrencia_ativo=safe_bool(row.get("tipo_ocorrencia_ativo")),
                        orgao_responsavel=safe_str(row.get("orgao_responsavel"), 64),
                        id_orgao_ocorrencia=safe_int(row.get("id_orgao_ocorrencia")),
                        ocorrencia_orgao_nome=safe_str(row.get("ocorrencia_orgao_nome"), 64),
                        codigo_ocorrencia_orgao=safe_int(row.get("codigo_ocorrencia_orgao")),
                        id_tipo_pessoa=safe_int(row.get("id_tipo_pessoa")),
                        tipo_pessoa_descricao=safe_str(row.get("tipo_pessoa_descricao"), 120),
                        id_ocupacao_pessoa=safe_int(row.get("id_ocupacao_pessoa")),
                        ocupacao_pessoa_descricao=safe_str(
                            row.get("ocupacao_pessoa_descricao"), 120
                        ),
                        id_tipo_frequencia=safe_int(row.get("id_tipo_frequencia")),
                        tipo_frequencia_descricao=safe_str(
                            row.get("tipo_frequencia_descricao"), 120
                        ),
                        ocupacao_drogas=safe_int(row.get("ocupacao_drogas")),
                        ocupacao_drogas_descricao=safe_str(
                            row.get("ocupacao_drogas_descricao"), 120
                        ),
                        id_item_praca=safe_int(row.get("id_item_praca")),
                        item_praca_descricao=safe_str(row.get("item_praca_descricao"), 255),
                    )
                )

                if limit is not None and stats["read"] >= limit:
                    break

            if objs:
                with transaction.atomic():
                    FatorUrbano.objects.bulk_create(
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
        self.stdout.write(f"  rows in db          : {FatorUrbano.objects.count()}")
