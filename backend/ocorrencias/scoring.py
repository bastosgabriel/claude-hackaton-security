"""Risk-score computation for ``AreaForca`` polygons.

For each polygon we compute three component densities (per km²), normalize
each to 0-100 across the polygon set with min-max, and combine them into a
single risk factor via a weighted average:

    oc_density  = Σ CRIME_WEIGHTS[desc_delito] * count(desc_delito) / area_km2
    den_density = count(denuncias)                                  / area_km2
    cam_density = count(cameras)                                    / area_km2

After min-max → oc_score, den_score, cam_coverage_score (all 0-100).
Cameras are a deterrent, so we invert:

    cam_score = 100 - cam_coverage_score

Final combined risk factor:

    score = Σ COMPONENT_WEIGHTS[c] * c_score   (for c in oc/den/cam)

When every polygon shares the same density for a component (or all zero),
that component's score collapses to 0 — ranking by it alone is undefined.
"""

from __future__ import annotations

import datetime as dt
from typing import Any

from django.db.models import Case, Count, F, FloatField, Sum, Value, When
from django.db.models.functions import TruncYear

from .models import AreaForca, Camera, DiskDenuncia, Ocorrencia

# Weight by crime type. Defaults reflect rough severity / impact:
#   - Roubo em coletivo:        1.2  (single event hits multiple victims)
#   - Roubo a transeunte:       1.0  (baseline)
#   - Roubo de aparelho celular: 0.8 (sub-type of street robbery, lower bodily-harm risk)
# Anything not in this map gets weight 1.0 (future-proof for new types).
CRIME_WEIGHTS: dict[str, float] = {
    "Roubo a transeunte":        1.0,
    "Roubo de aparelho celular": 0.8,
    "Roubo em coletivo":         1.2,
}
DEFAULT_WEIGHT = 1.0

# How the three component scores combine into the final risk factor.
# Must sum to 1.0 for the combined score to stay in [0, 100].
COMPONENT_WEIGHTS: dict[str, float] = {
    "ocorrencia": 0.5,
    "denuncia":   0.3,
    "camera":     0.2,
}


def _weight_case() -> Case:
    """SQL CASE returning the per-row weight, used inside a Sum aggregate."""
    whens = [When(desc_delito=k, then=Value(v)) for k, v in CRIME_WEIGHTS.items()]
    return Case(*whens, default=Value(DEFAULT_WEIGHT), output_field=FloatField())


def _minmax(values: list[float]) -> tuple[float, float, float]:
    lo = min(values)
    hi = max(values)
    return lo, hi, hi - lo


def _normalize(value: float, lo: float, span: float) -> float:
    return round(100.0 * (value - lo) / span, 2) if span > 0 else 0.0


def compute_scores(
    start_date: dt.date | None = None,
    end_date: dt.date | None = None,
) -> list[dict[str, Any]]:
    """Compute risk scores for every ``AreaForca`` polygon.

    Returns one dict per polygon with:
        fid, nome_subar, area_km2, geometry,
        occurrence_count, weighted_count, density, ocorrencia_score,
        denuncia_count, denuncia_density, denuncia_score,
        camera_count, camera_density, camera_score,
        score (combined 0-100), score_raw,
        by_desc_delito, by_year.
    """
    areas = list(AreaForca.objects.all().order_by("fid"))
    if not areas:
        return []

    oc_qs = Ocorrencia.objects.all()
    if start_date is not None:
        oc_qs = oc_qs.filter(data__gte=start_date)
    if end_date is not None:
        oc_qs = oc_qs.filter(data__lte=end_date)

    den_qs = DiskDenuncia.objects.all()
    if start_date is not None:
        den_qs = den_qs.filter(data_denuncia__date__gte=start_date)
    if end_date is not None:
        den_qs = den_qs.filter(data_denuncia__date__lte=end_date)

    # TODO: collapse the per-polygon loop into a single aggregate query
    # (e.g. ST_Contains join + group by area.fid) before scaling beyond a few
    # dozen polygons. Today: several queries × N areas.
    results: list[dict[str, Any]] = []
    for area in areas:
        oc_in_area = oc_qs.filter(location__within=area.geometry)
        agg = oc_in_area.aggregate(
            occurrence_count=Count("pk"),
            weighted_count=Sum(_weight_case()),
        )
        weighted = float(agg["weighted_count"] or 0.0)
        count = int(agg["occurrence_count"] or 0)
        oc_density = weighted / area.area_km2 if area.area_km2 > 0 else 0.0

        denuncia_count = den_qs.filter(location__within=area.geometry).count()
        den_density = denuncia_count / area.area_km2 if area.area_km2 > 0 else 0.0

        camera_count = Camera.objects.filter(location__within=area.geometry).count()
        cam_density = camera_count / area.area_km2 if area.area_km2 > 0 else 0.0

        by_desc = list(
            oc_in_area.values("desc_delito")
            .annotate(count=Count("pk"))
            .order_by("-count", "desc_delito")
        )
        by_year = [
            {"year": int(row["y"].year), "count": row["count"]}
            for row in oc_in_area.exclude(data__isnull=True)
            .annotate(y=TruncYear("data"))
            .values("y")
            .annotate(count=Count("pk"))
            .order_by("y")
        ]

        results.append({
            "fid":              area.fid,
            "nome_subar":       area.nome_subar,
            "area_km2":         area.area_km2,
            "geometry":         area.geometry,
            "occurrence_count": count,
            "weighted_count":   weighted,
            "density":          oc_density,
            "denuncia_count":   denuncia_count,
            "denuncia_density": den_density,
            "camera_count":     camera_count,
            "camera_density":   cam_density,
            "by_desc_delito":   by_desc,
            "by_year":          by_year,
        })

    oc_lo, _, oc_span = _minmax([r["density"] for r in results])
    den_lo, _, den_span = _minmax([r["denuncia_density"] for r in results])
    cam_lo, _, cam_span = _minmax([r["camera_density"] for r in results])

    w_oc = COMPONENT_WEIGHTS["ocorrencia"]
    w_den = COMPONENT_WEIGHTS["denuncia"]
    w_cam = COMPONENT_WEIGHTS["camera"]

    for r in results:
        oc_score = _normalize(r["density"], oc_lo, oc_span)
        den_score = _normalize(r["denuncia_density"], den_lo, den_span)
        cam_coverage = _normalize(r["camera_density"], cam_lo, cam_span)
        # Cameras deter crime → invert: more cameras lowers risk contribution.
        cam_score = round(100.0 - cam_coverage, 2)

        r["ocorrencia_score"] = oc_score
        r["denuncia_score"]   = den_score
        r["camera_score"]     = cam_score
        r["score_raw"]        = r["density"]
        r["score"] = round(
            w_oc * oc_score + w_den * den_score + w_cam * cam_score, 2
        )

    results.sort(key=lambda r: r["score"], reverse=True)
    return results
