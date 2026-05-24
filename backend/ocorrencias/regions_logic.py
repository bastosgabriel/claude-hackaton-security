"""Region-list payload for ``GET /api/regions/``.

Aggregates per-``AreaForca`` polygon stats into the shape the frontend
``RegionList`` panel expects. See ``docs/backend-handoff-regionlist.md``.

Reuses ``compute_scores`` for the headline score and computes four
operational criteria (``roubos_7d``, ``disque_denuncia``,
``fatores_ambientais``, ``historico_4s``) plus a ``relints_ativos`` stub
that is wired to zero until a RELINT data source exists.
"""

from __future__ import annotations

import datetime as dt
from typing import Any

from django.db.models import Count, Max

from .models import AreaForca, DiskDenuncia, FatorUrbano, Ocorrencia
from .scoring import compute_scores

# Crime descriptions that count as "roubo a transeunte family" for the
# headline ``roubos`` count and ``roubos_7d`` criterion.
ROUBO_DELITOS = [
    "Roubo a transeunte",
    "Roubo de aparelho celular",
    "Roubo em coletivo",
]

# Absolute cap for the ``fatores_ambientais`` criterion. The frontend
# shows ``"<count>/20"`` so the bar is scaled against this constant rather
# than against the cross-region min/max.
FATORES_CAP = 20


def _level_from_pct(pct: float) -> str:
    if pct >= 85:
        return "critico"
    if pct >= 70:
        return "alto"
    if pct >= 50:
        return "medio"
    return "baixo"


def _pct_minmax(values: list[float]) -> list[float]:
    if not values:
        return []
    lo, hi = min(values), max(values)
    if hi == lo:
        return [0.0] * len(values)
    return [100.0 * (v - lo) / (hi - lo) for v in values]


def _modal_aisp(geom, start_date: dt.date, end_date: dt.date) -> str:
    row = (
        Ocorrencia.objects.filter(
            location__within=geom,
            data__gte=start_date,
            data__lte=end_date,
            aisp__isnull=False,
        )
        .values("aisp")
        .annotate(count=Count("pk"))
        .order_by("-count", "aisp")
        .first()
    )
    return f"AISP {row['aisp']}" if row else ""


def _format_change(change_pct: float) -> str:
    rounded = round(change_pct)
    sign = "+" if rounded >= 0 else ""
    return f"{sign}{rounded}%"


def compute_region_list(
    start_date: dt.date,
    end_date: dt.date,
) -> list[dict[str, Any]]:
    """Build one region payload per ``AreaForca``, sorted by score desc."""
    scored = {r["fid"]: r for r in compute_scores(start_date, end_date)}

    # ``historico_4s`` compares the last 4 weeks vs. the previous 4 weeks,
    # anchored at end_date but capped to the latest date that actually has
    # data — otherwise a caller passing a future end_date gets a 0/0
    # comparison even when the dataset is rich.
    latest_data = Ocorrencia.objects.aggregate(mx=Max("data"))["mx"]
    hist_anchor = min(end_date, latest_data) if latest_data else end_date
    last4w_start = hist_anchor - dt.timedelta(weeks=4) + dt.timedelta(days=1)
    prev4w_end = last4w_start - dt.timedelta(days=1)
    prev4w_start = prev4w_end - dt.timedelta(weeks=4) + dt.timedelta(days=1)

    areas = list(AreaForca.objects.all().order_by("fid"))

    raw: list[dict[str, Any]] = []
    for area in areas:
        geom = area.geometry
        score_row = scored.get(area.fid, {})

        roubos = Ocorrencia.objects.filter(
            location__within=geom,
            desc_delito__in=ROUBO_DELITOS,
            data__gte=start_date,
            data__lte=end_date,
        ).count()

        denuncias = DiskDenuncia.objects.filter(
            location__within=geom,
            data_denuncia__date__gte=start_date,
            data_denuncia__date__lte=end_date,
        ).count()

        fatores_count = FatorUrbano.objects.filter(location__within=geom).count()

        last4w_count = Ocorrencia.objects.filter(
            location__within=geom,
            data__gte=last4w_start,
            data__lte=hist_anchor,
        ).count()
        prev4w_count = Ocorrencia.objects.filter(
            location__within=geom,
            data__gte=prev4w_start,
            data__lte=prev4w_end,
        ).count()
        if prev4w_count > 0:
            change_pct = 100.0 * (last4w_count - prev4w_count) / prev4w_count
        elif last4w_count == 0:
            change_pct = 0.0
        else:
            change_pct = 100.0

        raw.append({
            "area":          area,
            "score":         float(score_row.get("score", 0.0)),
            "roubos":        roubos,
            "denuncias":     denuncias,
            "fatores_count": fatores_count,
            "change_pct":    change_pct,
        })

    roubos_pcts = _pct_minmax([r["roubos"] for r in raw])
    denuncias_pcts = _pct_minmax([r["denuncias"] for r in raw])
    ambiente_pcts = [
        min(r["fatores_count"], FATORES_CAP) / FATORES_CAP * 100.0 for r in raw
    ]
    # Map change pct → 0–100 with neutral at 50: ±50% saturates the bar.
    historico_pcts = [
        max(0.0, min(100.0, 50.0 + r["change_pct"])) for r in raw
    ]

    results: list[dict[str, Any]] = []
    for i, r in enumerate(raw):
        area = r["area"]
        score = r["score"]
        fatores_display = min(r["fatores_count"], FATORES_CAP)
        ambiente_pct = ambiente_pcts[i]

        criteria = [
            {
                "key":   "roubos_7d",
                "label": "Roubos a transeunte",
                "value": str(r["roubos"]),
                "pct":   round(roubos_pcts[i]),
                "level": _level_from_pct(roubos_pcts[i]),
            },
            {
                "key":   "disque_denuncia",
                "label": "Disque Denúncia",
                "value": str(r["denuncias"]),
                "pct":   round(denuncias_pcts[i]),
                "level": _level_from_pct(denuncias_pcts[i]),
            },
            {
                "key":   "fatores_ambientais",
                "label": "Fatores ambientais",
                "value": f"{fatores_display}/{FATORES_CAP}",
                "pct":   round(ambiente_pct),
                "level": _level_from_pct(ambiente_pct),
            },
            {
                "key":   "relints_ativos",
                "label": "RELINTs ativos",
                "value": "0",
                "pct":   0,
                "level": "baixo",
            },
            {
                "key":   "historico_4s",
                "label": "Histórico 4 semanas",
                "value": _format_change(r["change_pct"]),
                "pct":   round(historico_pcts[i]),
                "level": _level_from_pct(historico_pcts[i]),
            },
        ]

        results.append({
            "id":        area.fid,
            "name":      area.nome_subar,
            "aisp":      _modal_aisp(area.geometry, start_date, end_date),
            "score":     round(score),
            "level":     _level_from_pct(score),
            "roubos":    r["roubos"],
            "denuncias": r["denuncias"],
            "ambiente":  round(ambiente_pct),
            "criteria":  criteria,
            "narrative": "",
            "actions":   [],
        })

    results.sort(key=lambda x: x["score"], reverse=True)
    return results
