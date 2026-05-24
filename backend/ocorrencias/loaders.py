"""Stand-alone loader functions for each source CSV.

Each ``load_*`` function takes a path + options and returns a stats dict. The
:mod:`ocorrencias.management.commands.load_data` Django command wires these
into a single CLI entrypoint via the :data:`DATASETS` registry below.
"""

from __future__ import annotations

import datetime as dt
import math
from pathlib import Path
from typing import Callable

import pandas as pd
from django.contrib.gis.geos import GEOSGeometry, Point
from django.db import transaction
from django.utils.timezone import is_naive, make_aware

from .models import AreaForca, Camera, DiskDenuncia, FatorUrbano, Ocorrencia

ReportFn = Callable[[str], None]
_NOOP: ReportFn = lambda msg: None

YEAR_MIN = 2000


# --------------------------------------------------------------------------
# Shared parsers
# --------------------------------------------------------------------------


def _is_nan(v: object) -> bool:
    return isinstance(v, float) and math.isnan(v)


def safe_str(raw: object, max_len: int | None = None) -> str:
    if raw is None or _is_nan(raw):
        return ""
    s = str(raw).strip()
    return s[:max_len] if max_len else s


def safe_int(raw: object) -> int | None:
    if raw is None or _is_nan(raw):
        return None
    s = str(raw).strip()
    if not s:
        return None
    try:
        return int(float(s))
    except (TypeError, ValueError):
        return None


def safe_float(raw: object, decimal_sep: str = ".") -> float | None:
    if raw is None or _is_nan(raw):
        return None
    s = str(raw).strip()
    if not s:
        return None
    if decimal_sep == ",":
        s = s.replace(".", "").replace(",", ".")
    try:
        return float(s)
    except (TypeError, ValueError):
        return None


def safe_bool(raw: object) -> bool | None:
    if raw is None or _is_nan(raw):
        return None
    s = str(raw).strip().upper()
    if not s:
        return None
    if s in {"TRUE", "T", "1", "SIM", "S", "YES", "Y"}:
        return True
    if s in {"FALSE", "F", "0", "NÃO", "NAO", "N", "NO"}:
        return False
    return None


def safe_coord(raw: object, decimal_sep: str = ".") -> float | None:
    v = safe_float(raw, decimal_sep=decimal_sep)
    return None if v is None or v == 0.0 else v


def parse_datetime(raw: object, fmt: str) -> dt.datetime | None:
    if raw is None or _is_nan(raw):
        return None
    s = str(raw).strip()
    if not s:
        return None
    try:
        parsed = dt.datetime.strptime(s, fmt)
    except ValueError:
        return None
    return make_aware(parsed) if is_naive(parsed) else parsed


def parse_date_ddmmyyyy(raw: object, ano: int | None) -> dt.date | None:
    """Parse DD/MM/YYYY; reject if year doesn't match ``ano`` or is implausible."""
    if raw is None or _is_nan(raw):
        return None
    s = str(raw).strip()
    if not s:
        return None
    try:
        parsed = dt.datetime.strptime(s, "%d/%m/%Y").date()
    except ValueError:
        return None
    if not (YEAR_MIN <= parsed.year <= dt.date.today().year + 1):
        return None
    if ano is not None and parsed.year != ano:
        return None
    return parsed


def parse_time(raw: object) -> dt.time | None:
    if raw is None or _is_nan(raw):
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


def _resolve(path: str | Path) -> Path:
    p = Path(path).expanduser().resolve()
    if not p.exists():
        raise FileNotFoundError(f"CSV not found: {p}")
    return p


# --------------------------------------------------------------------------
# Ocorrencias
# --------------------------------------------------------------------------


def load_ocorrencias(
    csv_path: str | Path,
    *,
    truncate: bool = False,
    limit: int | None = None,
    report: ReportFn = _NOOP,
) -> dict[str, int]:
    path = _resolve(csv_path)
    if truncate:
        n = Ocorrencia.objects.count()
        Ocorrencia.objects.all().delete()
        report(f"  truncated {n} ocorrencias rows")

    stats = {
        "read": 0, "imported": 0,
        "skipped_no_coord": 0, "skipped_no_id": 0, "date_nulled": 0,
    }
    reader = pd.read_csv(
        path, chunksize=10_000, dtype=str,
        keep_default_na=True, na_values=["", "nan", "NaN"],
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
            data = parse_date_ddmmyyyy(row.get("data"), ano)
            if data is None and row.get("data"):
                stats["date_nulled"] += 1
            objs.append(Ocorrencia(
                id_criptografado=pk,
                ano=ano or 0,
                mes=safe_int(row.get("mes")) or 0,
                data=data,
                hora=parse_time(row.get("hora")),
                delito=safe_int(row.get("delito")),
                desc_delito=safe_str(row.get("desc_delito"), 120),
                aisp=safe_int(row.get("aisp")),
                risp=safe_int(row.get("risp")),
                locf=safe_str(row.get("locf"), 255),
                dia_semana=safe_str(row.get("dia_semana"), 20),
                location=Point(lon, lat, srid=4326),
            ))
            if limit is not None and stats["read"] >= limit:
                break
        if objs:
            with transaction.atomic():
                Ocorrencia.objects.bulk_create(objs, batch_size=2_000, ignore_conflicts=True)
            stats["imported"] += len(objs)
        report(f"  chunk {chunk_idx + 1}: read={stats['read']} imported={stats['imported']}")
        if limit is not None and stats["read"] >= limit:
            break
    stats["rows_in_db"] = Ocorrencia.objects.count()
    return stats


# --------------------------------------------------------------------------
# Cameras
# --------------------------------------------------------------------------


def load_cameras(
    csv_path: str | Path,
    *,
    truncate: bool = False,
    limit: int | None = None,
    report: ReportFn = _NOOP,
) -> dict[str, int]:
    path = _resolve(csv_path)
    if truncate:
        n = Camera.objects.count()
        Camera.objects.all().delete()
        report(f"  truncated {n} cameras rows")
    stats = {"read": 0, "imported": 0, "skipped_no_geom": 0, "skipped_no_id": 0}
    reader = pd.read_csv(path, chunksize=1_000, dtype=str, keep_default_na=False)
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
            objs.append(Camera(
                id_ponto=pk,
                nome_area_fm=safe_str(row.get("nome_area_fm"), 120),
                id_trecho=safe_int(row.get("id_trecho")) or 0,
                location=geom,
            ))
            if limit is not None and stats["read"] >= limit:
                break
        if objs:
            with transaction.atomic():
                Camera.objects.bulk_create(objs, batch_size=500, ignore_conflicts=True)
            stats["imported"] += len(objs)
        report(f"  chunk {chunk_idx + 1}: read={stats['read']} imported={stats['imported']}")
        if limit is not None and stats["read"] >= limit:
            break
    stats["rows_in_db"] = Camera.objects.count()
    return stats


# --------------------------------------------------------------------------
# DiskDenuncia
# --------------------------------------------------------------------------

DISK_DENUNCIA_DT_FMT = "%m/%d/%Y %H:%M:%S"


def _parse_assunto_principal(raw: object) -> bool | None:
    i = safe_int(raw)
    if i is not None:
        return bool(i)
    return safe_bool(raw)


def load_disk_denuncia(
    csv_path: str | Path,
    *,
    truncate: bool = False,
    limit: int | None = None,
    report: ReportFn = _NOOP,
) -> dict[str, int]:
    path = _resolve(csv_path)
    if truncate:
        n = DiskDenuncia.objects.count()
        DiskDenuncia.objects.all().delete()
        report(f"  truncated {n} disk_denuncia rows")
    stats = {
        "read": 0, "parents": 0, "imported": 0,
        "skipped_child": 0, "skipped_no_id": 0, "skipped_no_coord": 0,
    }
    reader = pd.read_csv(
        path, chunksize=5_000, dtype=str, sep=";",
        encoding="latin-1", keep_default_na=False,
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
            location = Point(lng, lat, srid=4326) if lat is not None and lng is not None else None
            if location is None:
                stats["skipped_no_coord"] += 1
            objs.append(DiskDenuncia(
                id_denuncia=id_denuncia,
                numero_denuncia=numero,
                data_denuncia=parse_datetime(row.get("data_denuncia"), DISK_DENUNCIA_DT_FMT),
                data_difusao=parse_datetime(row.get("data_difusao"), DISK_DENUNCIA_DT_FMT),
                timestamp_insercao=parse_datetime(row.get("timestamp_insercao"), DISK_DENUNCIA_DT_FMT),
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
                assunto_principal=_parse_assunto_principal(row.get("assuntos.tipos.assunto_principal")),
                envolvido_id=safe_int(row.get("envolvidos.id")),
                envolvido_sexo=safe_str(row.get("envolvidos.sexo"), 1),
                envolvido_idade=safe_int(row.get("envolvidos.idade")),
                envolvido_pele=safe_str(row.get("envolvidos.pele"), 20),
                envolvido_estatura=safe_str(row.get("envolvidos.estatura"), 10),
                envolvido_porte=safe_str(row.get("envolvidos.porte"), 10),
                envolvido_cabelos=safe_str(row.get("envolvidos.cabelos"), 40),
                envolvido_olhos=safe_str(row.get("envolvidos.olhos"), 40),
                envolvido_outras_caracteristicas=safe_str(row.get("envolvidos.outras_caracteristicas")),
                status_denuncia=safe_str(row.get("status_denuncia"), 40),
                relato_redacted=safe_str(row.get("relato_redacted")),
            ))
            if limit is not None and stats["parents"] >= limit:
                break
        if objs:
            with transaction.atomic():
                DiskDenuncia.objects.bulk_create(objs, batch_size=1_000, ignore_conflicts=True)
            stats["imported"] += len(objs)
        report(
            f"  chunk {chunk_idx + 1}: read={stats['read']} "
            f"parents={stats['parents']} imported={stats['imported']}"
        )
        if limit is not None and stats["parents"] >= limit:
            break
    stats["rows_in_db"] = DiskDenuncia.objects.count()
    return stats


# --------------------------------------------------------------------------
# Fatores Urbanos
# --------------------------------------------------------------------------


def load_fatores_urbanos(
    csv_path: str | Path,
    *,
    truncate: bool = False,
    limit: int | None = None,
    report: ReportFn = _NOOP,
) -> dict[str, int]:
    path = _resolve(csv_path)
    if truncate:
        n = FatorUrbano.objects.count()
        FatorUrbano.objects.all().delete()
        report(f"  truncated {n} fatores_urbanos rows")
    stats = {"read": 0, "imported": 0, "skipped_no_id": 0, "skipped_no_coord": 0}
    reader = pd.read_csv(path, chunksize=2_000, dtype=str, keep_default_na=False)
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
                stats["skipped_no_id"] += 1
                continue
            objs.append(FatorUrbano(
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
                tipo_ocorrencia_descricao=safe_str(row.get("tipo_ocorrencia_descricao"), 255),
                tipo_ocorrencia_ativo=safe_bool(row.get("tipo_ocorrencia_ativo")),
                orgao_responsavel=safe_str(row.get("orgao_responsavel"), 64),
                id_orgao_ocorrencia=safe_int(row.get("id_orgao_ocorrencia")),
                ocorrencia_orgao_nome=safe_str(row.get("ocorrencia_orgao_nome"), 64),
                codigo_ocorrencia_orgao=safe_int(row.get("codigo_ocorrencia_orgao")),
                id_tipo_pessoa=safe_int(row.get("id_tipo_pessoa")),
                tipo_pessoa_descricao=safe_str(row.get("tipo_pessoa_descricao"), 120),
                id_ocupacao_pessoa=safe_int(row.get("id_ocupacao_pessoa")),
                ocupacao_pessoa_descricao=safe_str(row.get("ocupacao_pessoa_descricao"), 120),
                id_tipo_frequencia=safe_int(row.get("id_tipo_frequencia")),
                tipo_frequencia_descricao=safe_str(row.get("tipo_frequencia_descricao"), 120),
                ocupacao_drogas=safe_int(row.get("ocupacao_drogas")),
                ocupacao_drogas_descricao=safe_str(row.get("ocupacao_drogas_descricao"), 120),
                id_item_praca=safe_int(row.get("id_item_praca")),
                item_praca_descricao=safe_str(row.get("item_praca_descricao"), 255),
            ))
            if limit is not None and stats["read"] >= limit:
                break
        if objs:
            with transaction.atomic():
                FatorUrbano.objects.bulk_create(objs, batch_size=500, ignore_conflicts=True)
            stats["imported"] += len(objs)
        report(f"  chunk {chunk_idx + 1}: read={stats['read']} imported={stats['imported']}")
        if limit is not None and stats["read"] >= limit:
            break
    stats["rows_in_db"] = FatorUrbano.objects.count()
    return stats


# --------------------------------------------------------------------------
# Áreas de força (shapefile)
# --------------------------------------------------------------------------

# SIRGAS 2000 / UTM 23S — same metric CRS used elsewhere in the repo
# (visualize_areas_forca.py, print_geo_areas_forca.py) for km² computation.
AREAS_FORCA_METRIC_EPSG = 31983


def load_areas_forca(
    shp_path: str | Path,
    *,
    truncate: bool = False,
    limit: int | None = None,
    report: ReportFn = _NOOP,
) -> dict[str, int]:
    import geopandas as gpd  # local: only needed for this loader

    path = _resolve(shp_path)
    if truncate:
        n = AreaForca.objects.count()
        AreaForca.objects.all().delete()
        report(f"  truncated {n} areas_forca rows")

    stats = {"read": 0, "imported": 0, "skipped_no_fid": 0, "skipped_bad_geom": 0}
    # reset_index keeps the loop's positional `i` aligned with both the WGS84
    # and the metric GeoDataFrames regardless of the shapefile's own FID.
    gdf = gpd.read_file(path).to_crs(epsg=4326).reset_index(drop=True)
    gdf_m = gdf.to_crs(epsg=AREAS_FORCA_METRIC_EPSG)

    objs: list[AreaForca] = []
    for i, row in gdf.iterrows():
        stats["read"] += 1
        fid = safe_int(row.get("fid"))
        if fid is None:
            stats["skipped_no_fid"] += 1
            if limit is not None and stats["read"] >= limit:
                break
            continue
        geom = row.geometry
        if geom is None or geom.is_empty or not geom.is_valid:
            stats["skipped_bad_geom"] += 1
            if limit is not None and stats["read"] >= limit:
                break
            continue
        # Force a single Polygon (shapefile is all Polygon; if a feature is
        # MultiPolygon, fall back to the largest part).
        if geom.geom_type == "MultiPolygon":
            geom = max(geom.geoms, key=lambda g: g.area)
        try:
            poly = GEOSGeometry(geom.wkt, srid=4326)
        except Exception:
            stats["skipped_bad_geom"] += 1
            if limit is not None and stats["read"] >= limit:
                break
            continue
        area_km2 = float(gdf_m.geometry.loc[i].area) / 1_000_000.0
        objs.append(AreaForca(
            fid=fid,
            nome_subar=safe_str(row.get("nome_subar"), 255),
            area_km2=area_km2,
            geometry=poly,
        ))
        if limit is not None and stats["read"] >= limit:
            break
    if objs:
        with transaction.atomic():
            AreaForca.objects.bulk_create(objs, batch_size=100, ignore_conflicts=True)
        stats["imported"] = len(objs)
    report(f"  loaded {stats['imported']} polygons from {path.name}")
    stats["rows_in_db"] = AreaForca.objects.count()
    return stats


# --------------------------------------------------------------------------
# Registry: declared order is the load order.
# --------------------------------------------------------------------------

DATASETS: dict[str, tuple[str, Callable[..., dict[str, int]]]] = {
    "ocorrencias":     ("df_ocorrencias_tratado - Extração 1 .csv", load_ocorrencias),
    "cameras":         ("cameras_areas_fm.csv",                      load_cameras),
    "disk_denuncia":   ("disk_denuncia.csv",                         load_disk_denuncia),
    "fatores_urbanos": ("fatores_urbanos.csv",                       load_fatores_urbanos),
    "areas_forca":     ("sh_area_forca/areas_forca_municipal.shp",   load_areas_forca),
}
