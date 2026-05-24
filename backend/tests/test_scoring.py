"""Tests for the risk-scoring pipeline and /api/areas-forca/scores/."""

from __future__ import annotations

import datetime as dt

import pytest
from django.contrib.gis.geos import Point, Polygon
from rest_framework.test import APIClient

from ocorrencias.models import AreaForca, Ocorrencia
from ocorrencias.scoring import CRIME_WEIGHTS, compute_scores

URL = "/api/areas-forca/scores/"


def _square(min_lat: float, max_lat: float, min_lng: float, max_lng: float) -> Polygon:
    """Build a 4326 polygon from a [lat, lng] bbox."""
    ring = [
        (min_lng, min_lat),
        (max_lng, min_lat),
        (max_lng, max_lat),
        (min_lng, max_lat),
        (min_lng, min_lat),
    ]
    return Polygon(ring, srid=4326)


def make_area(fid: int, name: str, *, min_lat, max_lat, min_lng, max_lng, area_km2=1.0):
    return AreaForca.objects.create(
        fid=fid,
        nome_subar=name,
        area_km2=area_km2,
        geometry=_square(min_lat, max_lat, min_lng, max_lng),
    )


def make_oc(
    pk: str,
    lat: float,
    lng: float,
    data: dt.date,
    desc: str = "Roubo a transeunte",
):
    return Ocorrencia.objects.create(
        id_criptografado=pk,
        ano=data.year,
        mes=data.month,
        data=data,
        desc_delito=desc,
        aisp=5,
        risp=1,
        locf="Rua Test",
        location=Point(lng, lat, srid=4326),
    )


@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
def two_areas(db):
    # Area A: 1 km², 2 transeunte + 1 celular  (weighted = 2*1.0 + 1*0.8 = 2.8 → density = 2.8)
    # Area B: 2 km², 1 coletivo                (weighted = 1*1.2          = 1.2 → density = 0.6)
    a = make_area(1, "Area A", min_lat=-22.95, max_lat=-22.90, min_lng=-43.22, max_lng=-43.17, area_km2=1.0)
    b = make_area(2, "Area B", min_lat=-22.80, max_lat=-22.75, min_lng=-43.10, max_lng=-43.05, area_km2=2.0)
    # Inside A
    make_oc("a" * 64, -22.92, -43.19, dt.date(2023, 3, 10), "Roubo a transeunte")
    make_oc("b" * 64, -22.93, -43.20, dt.date(2023, 6, 1),  "Roubo a transeunte")
    make_oc("c" * 64, -22.91, -43.18, dt.date(2024, 1, 15), "Roubo de aparelho celular")
    # Inside B
    make_oc("d" * 64, -22.77, -43.07, dt.date(2023, 7, 4),  "Roubo em coletivo")
    # Outside both
    make_oc("e" * 64, -23.50, -46.60, dt.date(2023, 3, 10), "Roubo a transeunte")
    return a, b


def test_compute_scores_basic(two_areas):
    result = compute_scores()
    assert len(result) == 2
    by_fid = {r["fid"]: r for r in result}

    a, b = by_fid[1], by_fid[2]
    assert a["occurrence_count"] == 3
    assert b["occurrence_count"] == 1

    assert a["weighted_count"] == pytest.approx(2 * 1.0 + 1 * 0.8)
    assert b["weighted_count"] == pytest.approx(1 * 1.2)

    assert a["density"] == pytest.approx(2.8 / 1.0)
    assert b["density"] == pytest.approx(1.2 / 2.0)

    # Min-max normalization: A is the max → 100, B is the min → 0.
    assert a["score"] == pytest.approx(100.0)
    assert b["score"] == pytest.approx(0.0)


def test_compute_scores_orders_by_score_desc(two_areas):
    result = compute_scores()
    assert [r["fid"] for r in result] == [1, 2]


def test_compute_scores_date_window_filters(two_areas):
    # Window covers only the 2024 occurrence in A → A has 1 celular (weighted 0.8); B has 0.
    result = compute_scores(start_date=dt.date(2024, 1, 1), end_date=dt.date(2024, 12, 31))
    by_fid = {r["fid"]: r for r in result}
    assert by_fid[1]["occurrence_count"] == 1
    assert by_fid[1]["weighted_count"] == pytest.approx(0.8)
    assert by_fid[2]["occurrence_count"] == 0


def test_compute_scores_zero_occurrences_returns_zero(db):
    make_area(1, "Empty A", min_lat=-22.95, max_lat=-22.90, min_lng=-43.22, max_lng=-43.17)
    make_area(2, "Empty B", min_lat=-22.80, max_lat=-22.75, min_lng=-43.10, max_lng=-43.05)
    result = compute_scores()
    assert all(r["score"] == 0.0 for r in result)
    assert all(r["occurrence_count"] == 0 for r in result)


def test_compute_scores_no_areas_returns_empty(db):
    assert compute_scores() == []


def test_endpoint_returns_geojson_and_score(client, two_areas):
    r = client.get(URL)
    assert r.status_code == 200, r.content
    body = r.json()
    assert body["weights"] == CRIME_WEIGHTS
    assert body["date_range"]["end_date"] == dt.date.today().isoformat()
    assert len(body["results"]) == 2
    top = body["results"][0]
    assert top["fid"] == 1
    assert top["score"] == 100.0
    assert top["geometry"]["type"] == "Polygon"
    assert "coordinates" in top["geometry"]
    descs = {row["desc_delito"]: row["count"] for row in top["by_desc_delito"]}
    assert descs == {"Roubo a transeunte": 2, "Roubo de aparelho celular": 1}


def test_endpoint_with_date_window(client, two_areas):
    r = client.get(URL, {"start_date": "2024-01-01", "end_date": "2024-12-31"})
    assert r.status_code == 200
    by_fid = {row["fid"]: row for row in r.json()["results"]}
    assert by_fid[1]["occurrence_count"] == 1
    assert by_fid[2]["occurrence_count"] == 0


def test_endpoint_rejects_inverted_date_range(client, db):
    r = client.get(URL, {"start_date": "2024-12-31", "end_date": "2024-01-01"})
    assert r.status_code == 400
