"""Tests for /api/ocorrencias/search/."""

from __future__ import annotations

import datetime as dt

import pytest
from django.contrib.gis.geos import Point
from rest_framework.test import APIClient

from ocorrencias.models import Ocorrencia

URL = "/api/ocorrencias/search/"


def make_oc(pk: str, lat: float, lng: float, data: dt.date, desc: str = "Roubo a transeunte", aisp: int = 5):
    return Ocorrencia.objects.create(
        id_criptografado=pk,
        ano=data.year,
        mes=data.month,
        data=data,
        desc_delito=desc,
        aisp=aisp,
        risp=1,
        locf="Rua Test",
        location=Point(lng, lat, srid=4326),
    )


@pytest.fixture
def seeded(db):
    make_oc("a" * 64, -22.91, -43.18, dt.date(2023, 3, 10))
    make_oc("b" * 64, -22.92, -43.19, dt.date(2023, 3, 15), desc="Furto", aisp=6)
    make_oc("c" * 64, -22.93, -43.20, dt.date(2023, 6, 1))
    make_oc("d" * 64, -23.50, -46.60, dt.date(2023, 3, 10))  # outside
    make_oc("e" * 64, -22.91, -43.18, dt.date(2020, 1, 1))  # before window


@pytest.fixture
def client():
    return APIClient()


def _box(min_lat, max_lat, min_lng, max_lng):
    # Closed ring of 5 [lat, lng] points.
    return [
        [min_lat, min_lng],
        [min_lat, max_lng],
        [max_lat, max_lng],
        [max_lat, min_lng],
        [min_lat, min_lng],
    ]


def test_polygon_returns_inside_points(client, seeded):
    payload = {
        "polygon": _box(-22.95, -22.90, -43.22, -43.17),
        "start_date": "2023-01-01",
        "end_date": "2023-12-31",
    }
    r = client.post(URL, payload, format="json")
    assert r.status_code == 200, r.content
    body = r.json()
    assert body["summary"]["total"] == 3
    ids = {row["id"] for row in body["results"]}
    assert ids == {"a" * 64, "b" * 64, "c" * 64}
    by_desc = {row["desc_delito"]: row["count"] for row in body["summary"]["by_desc_delito"]}
    assert by_desc == {"Roubo a transeunte": 2, "Furto": 1}


def test_polygon_outside_rio_is_empty(client, seeded):
    payload = {
        "polygon": _box(-1.0, -0.5, -50.0, -49.5),
        "start_date": "2023-01-01",
        "end_date": "2023-12-31",
    }
    r = client.post(URL, payload, format="json")
    assert r.status_code == 200
    body = r.json()
    assert body["summary"]["total"] == 0
    assert body["results"] == []


def test_invalid_polygon_too_few_points(client, db):
    payload = {
        "polygon": [[-22.91, -43.18], [-22.92, -43.19]],
        "start_date": "2023-01-01",
        "end_date": "2023-12-31",
    }
    r = client.post(URL, payload, format="json")
    assert r.status_code == 400


def test_date_range_inverted(client, db):
    payload = {
        "polygon": _box(-22.95, -22.90, -43.22, -43.17),
        "start_date": "2023-12-31",
        "end_date": "2023-01-01",
    }
    r = client.post(URL, payload, format="json")
    assert r.status_code == 400


def test_null_data_rows_excluded(client, seeded):
    Ocorrencia.objects.create(
        id_criptografado="f" * 64,
        ano=2023,
        mes=3,
        data=None,
        desc_delito="Roubo a transeunte",
        aisp=5,
        risp=1,
        locf="Rua Sem Data",
        location=Point(-43.18, -22.91, srid=4326),
    )
    payload = {
        "polygon": _box(-22.95, -22.90, -43.22, -43.17),
        "start_date": "2023-01-01",
        "end_date": "2023-12-31",
    }
    r = client.post(URL, payload, format="json")
    body = r.json()
    ids = {row["id"] for row in body["results"]}
    assert "f" * 64 not in ids


def test_pagination_caps_results(client, db):
    base = dt.date(2023, 1, 1)
    for i in range(7):
        make_oc(f"{i:064d}", -22.91, -43.18, base + dt.timedelta(days=i))
    payload = {
        "polygon": _box(-22.95, -22.90, -43.22, -43.17),
        "start_date": "2023-01-01",
        "end_date": "2023-12-31",
        "page": 1,
        "page_size": 3,
    }
    r = client.post(URL, payload, format="json")
    body = r.json()
    assert body["summary"]["total"] == 7
    assert len(body["results"]) == 3
    assert body["pagination"]["total_pages"] == 3
