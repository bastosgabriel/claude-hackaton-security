"""Risk-score computation for ``AreaForca`` polygons.

For each polygon, the score is a weighted occurrence density (per km²)
normalized to 0–100 across the set of polygons being scored together.

    weighted_count = Σ  CRIME_WEIGHTS[desc_delito] * count(desc_delito)
    density        = weighted_count / area_km2
    score          = 100 * (density - min) / (max - min)

When all polygons have the same density (or zero occurrences), every score
is 0 — the relative ranking is undefined.
"""

from __future__ import annotations

import datetime as dt
from typing import Any

from django.db.models import Case, Count, F, FloatField, Sum, Value, When
from django.db.models.functions import TruncYear

from .models import AreaForca, Ocorrencia

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


def _weight_case() -> Case:
    """SQL CASE returning the per-row weight, used inside a Sum aggregate."""
    whens = [When(desc_delito=k, then=Value(v)) for k, v in CRIME_WEIGHTS.items()]
    return Case(*whens, default=Value(DEFAULT_WEIGHT), output_field=FloatField())


def compute_scores(
    start_date: dt.date | None = None,
    end_date: dt.date | None = None,
) -> list[dict[str, Any]]:
    """Compute risk scores for every ``AreaForca`` polygon.

    Returns one dict per polygon with: fid, nome_subar, area_km2, geometry,
    occurrence_count, weighted_count, density, score (0-100), score_raw,
    by_desc_delito, by_year.
    """
    areas = list(AreaForca.objects.all().order_by("fid"))
    if not areas:
        return []

    base_qs = Ocorrencia.objects.all()
    if start_date is not None:
        base_qs = base_qs.filter(data__gte=start_date)
    if end_date is not None:
        base_qs = base_qs.filter(data__lte=end_date)

    # TODO: collapse the per-polygon loop into a single aggregate query
    # (e.g. ST_Contains join + group by area.fid) before scaling beyond a few
    # dozen polygons. Today: 3 queries × N areas.
    results: list[dict[str, Any]] = []
    for area in areas:
        qs = base_qs.filter(location__within=area.geometry)
        agg = qs.aggregate(
            occurrence_count=Count("pk"),
            weighted_count=Sum(_weight_case()),
        )
        weighted = float(agg["weighted_count"] or 0.0)
        count = int(agg["occurrence_count"] or 0)
        density = weighted / area.area_km2 if area.area_km2 > 0 else 0.0

        by_desc = list(
            qs.values("desc_delito")
            .annotate(count=Count("pk"))
            .order_by("-count", "desc_delito")
        )
        by_year = [
            {"year": int(row["y"].year), "count": row["count"]}
            for row in qs.exclude(data__isnull=True)
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
            "density":          density,
            "by_desc_delito":   by_desc,
            "by_year":          by_year,
        })

    densities = [r["density"] for r in results]
    lo, hi = min(densities), max(densities)
    span = hi - lo
    for r in results:
        r["score_raw"] = r["density"]
        r["score"] = round(100.0 * (r["density"] - lo) / span, 2) if span > 0 else 0.0

    results.sort(key=lambda r: r["score"], reverse=True)
    return results
