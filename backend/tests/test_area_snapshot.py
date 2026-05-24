"""Tests for /api/area-snapshot/ and /api/areas-forca/."""

from __future__ import annotations

import datetime as dt

import pytest
from django.contrib.gis.geos import Point, Polygon
from django.utils import timezone
from rest_framework.test import APIClient

from ocorrencias.models import (
    AreaForca,
    Camera,
    DiskDenuncia,
    FatorUrbano,
    Ocorrencia,
)

SNAPSHOT_URL = "/api/area-snapshot/"
AREAS_URL = "/api/areas-forca/"


def _box(min_lat, max_lat, min_lng, max_lng) -> Polygon:
    ring = [
        (min_lng, min_lat),
        (max_lng, min_lat),
        (max_lng, max_lat),
        (min_lng, max_lat),
        (min_lng, min_lat),
    ]
    return Polygon(ring, srid=4326)


@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
def seeded(db):
    AreaForca.objects.create(
        fid=1,
        nome_subar="Centro Teste",
        area_km2=0.5,
        geometry=_box(-22.95, -22.90, -43.22, -43.17),
    )
    AreaForca.objects.create(
        fid=99,
        nome_subar="Outside Teste",
        area_km2=0.5,
        geometry=_box(-23.55, -23.45, -46.65, -46.55),  # São Paulo box
    )
    Ocorrencia.objects.create(
        id_criptografado="o" * 64,
        data=dt.date(2023, 3, 10),
        desc_delito="Roubo",
        aisp=5,
        risp=1,
        locf="Rua A",
        location=Point(-43.18, -22.91, srid=4326),
    )
    DiskDenuncia.objects.create(
        id_denuncia=999,
        numero_denuncia="123.4.2023",
        data_denuncia=timezone.make_aware(dt.datetime(2023, 3, 12, 10, 0)),
        classe="Drogas",
        tipo="Consumo",
        location=Point(-43.185, -22.915, srid=4326),
    )
    DiskDenuncia.objects.create(
        id_denuncia=998,
        numero_denuncia="123.5.2020",
        data_denuncia=timezone.make_aware(dt.datetime(2020, 1, 1, 10, 0)),
        classe="Drogas",
        tipo="Trafico",
        location=Point(-43.185, -22.915, srid=4326),
    )
    Camera.objects.create(
        id_ponto="cam-1",
        nome_area_fm="Centro",
        id_trecho=1,
        location=Point(-43.19, -22.92, srid=4326),
    )
    Camera.objects.create(
        id_ponto="cam-far",
        nome_area_fm="Outside",
        id_trecho=2,
        location=Point(-46.6, -23.5, srid=4326),
    )
    FatorUrbano.objects.create(
        id_resposta_ocorrencia=42,
        id_tipo_ocorrencia=5,
        tipo_ocorrencia_descricao="Vegetação obstruindo",
        bairro_nome="Meier",
        location=Point(-43.20, -22.93, srid=4326),
    )


def test_areas_forca_list_returns_geojson(client, seeded):
    r = client.get(AREAS_URL)
    assert r.status_code == 200, r.content
    body = r.json()
    assert body["type"] == "FeatureCollection"
    fids = {f["properties"]["fid"] for f in body["features"]}
    assert fids == {1, 99}
    first = body["features"][0]
    assert first["type"] == "Feature"
    assert first["geometry"]["type"] in {"Polygon", "MultiPolygon"}
    assert {"fid", "nome_subar", "area_km2"} <= set(first["properties"])


def test_snapshot_returns_all_datasets_for_area(client, seeded):
    payload = {"fid": 1, "start_date": "2023-01-01", "end_date": "2023-12-31"}
    r = client.post(SNAPSHOT_URL, payload, format="json")
    assert r.status_code == 200, r.content
    body = r.json()
    assert body["area_forca"]["fid"] == 1
    assert body["area_forca"]["nome_subar"] == "Centro Teste"
    assert set(body.keys()) == {"area_forca", "ocorrencias", "denuncias", "cameras", "fatores_urbanos"}
    assert body["ocorrencias"]["summary"]["total"] == 1
    assert body["denuncias"]["summary"]["total"] == 1
    assert body["cameras"]["summary"]["total"] == 1
    assert body["fatores_urbanos"]["summary"]["total"] == 1


def test_snapshot_date_filter_only_applies_to_dated_tables(client, seeded):
    payload = {"fid": 1, "start_date": "2024-01-01", "end_date": "2024-01-02"}
    r = client.post(SNAPSHOT_URL, payload, format="json")
    assert r.status_code == 200
    body = r.json()
    assert body["ocorrencias"]["summary"]["total"] == 0
    assert body["denuncias"]["summary"]["total"] == 0
    assert body["cameras"]["summary"]["total"] == 1
    assert body["fatores_urbanos"]["summary"]["total"] == 1


def test_snapshot_unknown_fid_returns_404(client, seeded):
    payload = {"fid": 12345, "start_date": "2023-01-01", "end_date": "2023-12-31"}
    r = client.post(SNAPSHOT_URL, payload, format="json")
    assert r.status_code == 404


def test_snapshot_invalid_date_range_rejected(client, seeded):
    payload = {"fid": 1, "start_date": "2023-12-31", "end_date": "2023-01-01"}
    r = client.post(SNAPSHOT_URL, payload, format="json")
    assert r.status_code == 400


def test_snapshot_uses_correct_area(client, seeded):
    payload = {"fid": 99, "start_date": "2023-01-01", "end_date": "2023-12-31"}
    r = client.post(SNAPSHOT_URL, payload, format="json")
    body = r.json()
    assert body["cameras"]["summary"]["total"] == 1
    assert body["cameras"]["results"][0]["id"] == "cam-far"
    assert body["ocorrencias"]["summary"]["total"] == 0
