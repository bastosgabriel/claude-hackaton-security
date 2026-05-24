"""Tests for the risk-scoring pipeline and /api/areas-forca/scores/."""

from __future__ import annotations

import datetime as dt

import pytest
from django.contrib.gis.geos import Point, Polygon
from rest_framework.test import APIClient

from ocorrencias.models import AreaForca, Camera, DiskDenuncia, Ocorrencia
from ocorrencias.scoring import COMPONENT_WEIGHTS, CRIME_WEIGHTS, compute_scores

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
        data=data,
        desc_delito=desc,
        aisp=5,
        risp=1,
        locf="Rua Test",
        location=Point(lng, lat, srid=4326),
    )


def make_denuncia(pk: int, lat: float, lng: float, when: dt.datetime):
    return DiskDenuncia.objects.create(
        id_denuncia=pk,
        numero_denuncia=f"D{pk:06d}",
        data_denuncia=when,
        location=Point(lng, lat, srid=4326),
    )


def make_camera(pk: str, lat: float, lng: float, area_name: str = "X"):
    return Camera.objects.create(
        id_ponto=pk,
        nome_area_fm=area_name,
        id_trecho=1,
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

    # Occurrence component: A is the max → 100, B is the min → 0.
    assert a["ocorrencia_score"] == pytest.approx(100.0)
    assert b["ocorrencia_score"] == pytest.approx(0.0)

    # No denuncias / cameras anywhere → den span and cam span are both 0.
    # den_score collapses to 0; cam_coverage collapses to 0 so cam_score = 100.
    assert a["denuncia_score"] == 0.0
    assert b["denuncia_score"] == 0.0
    assert a["camera_score"] == 100.0
    assert b["camera_score"] == 100.0

    # Combined: w_oc*oc + w_den*den + w_cam*cam_score
    expected_a = (
        COMPONENT_WEIGHTS["ocorrencia"] * 100.0
        + COMPONENT_WEIGHTS["camera"] * 100.0
    )
    expected_b = COMPONENT_WEIGHTS["camera"] * 100.0
    assert a["score"] == pytest.approx(expected_a)
    assert b["score"] == pytest.approx(expected_b)


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


def test_compute_scores_zero_signals_collapses(db):
    # All polygons share identical (zero) signals → every component span = 0.
    # Spec: each component normalizes to 0; camera_score = 100 - 0 = 100, so
    # every polygon gets the same combined score (the camera contribution).
    make_area(1, "Empty A", min_lat=-22.95, max_lat=-22.90, min_lng=-43.22, max_lng=-43.17)
    make_area(2, "Empty B", min_lat=-22.80, max_lat=-22.75, min_lng=-43.10, max_lng=-43.05)
    result = compute_scores()
    assert all(r["occurrence_count"] == 0 for r in result)
    assert all(r["denuncia_count"] == 0 for r in result)
    assert all(r["camera_count"] == 0 for r in result)
    expected = COMPONENT_WEIGHTS["camera"] * 100.0
    assert all(r["score"] == pytest.approx(expected) for r in result)


def test_compute_scores_no_areas_returns_empty(db):
    assert compute_scores() == []


def test_endpoint_returns_geojson_and_score(client, two_areas):
    r = client.get(URL)
    assert r.status_code == 200, r.content
    body = r.json()
    assert body["weights"] == CRIME_WEIGHTS
    assert body["component_weights"] == COMPONENT_WEIGHTS
    assert body["date_range"]["end_date"] == dt.date.today().isoformat()
    assert len(body["results"]) == 2
    top = body["results"][0]
    assert top["fid"] == 1
    assert top["ocorrencia_score"] == 100.0
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


def test_compute_scores_denuncia_component(db):
    # Identical occurrences (no signal there) but A has 3 denuncias, B has 0.
    a = make_area(1, "Area A", min_lat=-22.95, max_lat=-22.90, min_lng=-43.22, max_lng=-43.17, area_km2=1.0)
    b = make_area(2, "Area B", min_lat=-22.80, max_lat=-22.75, min_lng=-43.10, max_lng=-43.05, area_km2=1.0)
    when = dt.datetime(2024, 6, 1, 12, 0, tzinfo=dt.timezone.utc)
    make_denuncia(1, -22.92, -43.19, when)
    make_denuncia(2, -22.93, -43.20, when)
    make_denuncia(3, -22.91, -43.18, when)

    result = compute_scores()
    by_fid = {r["fid"]: r for r in result}
    assert by_fid[1]["denuncia_count"] == 3
    assert by_fid[2]["denuncia_count"] == 0
    assert by_fid[1]["denuncia_score"] == 100.0
    assert by_fid[2]["denuncia_score"] == 0.0


def test_compute_scores_camera_inverse(db):
    # A has 4 cameras, B has none → A is "better protected" → camera_score lower for A.
    a = make_area(1, "Area A", min_lat=-22.95, max_lat=-22.90, min_lng=-43.22, max_lng=-43.17, area_km2=1.0)
    b = make_area(2, "Area B", min_lat=-22.80, max_lat=-22.75, min_lng=-43.10, max_lng=-43.05, area_km2=1.0)
    for i in range(4):
        make_camera(f"cam-{i}", -22.92, -43.19)

    result = compute_scores()
    by_fid = {r["fid"]: r for r in result}
    assert by_fid[1]["camera_count"] == 4
    assert by_fid[2]["camera_count"] == 0
    # A has all the cameras → max coverage → camera_score = 0
    # B has none → min coverage → camera_score = 100
    assert by_fid[1]["camera_score"] == 0.0
    assert by_fid[2]["camera_score"] == 100.0


def test_compute_scores_denuncia_date_window(db):
    a = make_area(1, "Area A", min_lat=-22.95, max_lat=-22.90, min_lng=-43.22, max_lng=-43.17)
    b = make_area(2, "Area B", min_lat=-22.80, max_lat=-22.75, min_lng=-43.10, max_lng=-43.05)
    make_denuncia(1, -22.92, -43.19, dt.datetime(2023, 1, 5, tzinfo=dt.timezone.utc))
    make_denuncia(2, -22.92, -43.19, dt.datetime(2024, 6, 1, tzinfo=dt.timezone.utc))

    result = compute_scores(start_date=dt.date(2024, 1, 1), end_date=dt.date(2024, 12, 31))
    by_fid = {r["fid"]: r for r in result}
    assert by_fid[1]["denuncia_count"] == 1


def test_compute_scores_combined_formula(db):
    # Two areas, distinct signals on every channel, all max-vs-min so the
    # weighted-average is easy to spell out arithmetically.
    a = make_area(1, "Area A", min_lat=-22.95, max_lat=-22.90, min_lng=-43.22, max_lng=-43.17, area_km2=1.0)
    b = make_area(2, "Area B", min_lat=-22.80, max_lat=-22.75, min_lng=-43.10, max_lng=-43.05, area_km2=1.0)
    # A: lots of occurrences and denuncias, no cameras → high risk
    make_oc("a" * 64, -22.92, -43.19, dt.date(2024, 1, 1))
    make_oc("b" * 64, -22.93, -43.20, dt.date(2024, 2, 1))
    make_denuncia(1, -22.92, -43.19, dt.datetime(2024, 3, 1, tzinfo=dt.timezone.utc))
    # B: zero occurrences/denuncias, one camera → low risk
    make_camera("cam-b", -22.77, -43.07)

    result = compute_scores()
    by_fid = {r["fid"]: r for r in result}
    expected_a = (
        COMPONENT_WEIGHTS["ocorrencia"] * 100.0
        + COMPONENT_WEIGHTS["denuncia"]  * 100.0
        + COMPONENT_WEIGHTS["camera"]    * 100.0  # A has 0 cameras → max risk on camera channel
    )
    expected_b = (
        COMPONENT_WEIGHTS["ocorrencia"] * 0.0
        + COMPONENT_WEIGHTS["denuncia"]  * 0.0
        + COMPONENT_WEIGHTS["camera"]    * 0.0    # B has all the cameras → min risk on camera channel
    )
    assert by_fid[1]["score"] == pytest.approx(expected_a)
    assert by_fid[2]["score"] == pytest.approx(expected_b)
    # Sort order: A first (higher combined risk).
    assert [r["fid"] for r in result] == [1, 2]
