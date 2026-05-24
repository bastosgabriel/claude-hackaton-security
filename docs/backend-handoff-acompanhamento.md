# Backend handoff — Acompanhamento panel

Audience: backend dev wiring the right-hand "Acompanhamento" panel of the **Avaliação** tab (`frontend/components/compstat/AvaliacaoView.tsx`) to real data. Today everything in that panel is hard-coded — `DELTAS`, `CHECKLIST`, `TIMELINE` constants at the top of the file. This document spells out what the UI shows, what data must come from the backend, and which of that already exists vs. needs new work.

For the related "Region ranking list" work see [`docs/backend-handoff-regionlist.md`](./backend-handoff-regionlist.md). For the "before/after" maps on the left of the same tab no backend work is needed — they reuse `GET /api/areas-forca/scores/` with different date windows.

## Component recap

- File: `frontend/components/compstat/AvaliacaoView.tsx` — the Acompanhamento card lives at the right of the tab's two-column grid.
- It is **per-region** and **per-week**: it summarises one área de força over a single 7-day window, comparing it against the prior 7 days.
- Four sub-sections, from top to bottom:
  1. **Header** — region name + AISP + week range + a one-word verdict badge (Melhora / Estável / Piora).
  2. **Resultados** — 4 KPI cards, each showing the % change vs. the prior week, plus the raw `before → after` numbers.
  3. **Ações executadas** — a checklist of actions taken during the week, with completion date or "pendente".
  4. **Marcos da semana** — a timeline of 3-5 notable events with timestamps.

The mock today covers a single region ("Lapa-Centro · AISP 5") and a single week ("13–19 mai"). The endpoint needs to support any `(fid, week_start)` pair.

## What the backend already has

- `Ocorrencia` (`backend/ocorrencias/models.py`) — `data`, `desc_delito`, `aisp`, `location`. **Enough to compute** the "Roubos a transeunte" delta over a polygon for two adjacent date windows.
- `DiskDenuncia` — `data_denuncia`, `classe`, `location`. **Enough to compute** the "Disque Denúncia" delta the same way.
- `AreaForca` — polygons + `fid` (the per-region key).
- `compute_scores(start_date, end_date)` at `backend/ocorrencias/scoring.py` — already used by `AreaForcaScoreListView`. Can be called twice (prior week, current week) to derive the headline `melhora / estável / piora` verdict from the score delta.

So sections 1 and 2's "Roubos" and "Disque Denúncia" cards are derivable with zero new ingest work. The other KPIs and sections 3 & 4 need new data sources.

## Proposed endpoint

Add a single endpoint scoped to one region + one week:

```
GET /api/regions/{fid}/acompanhamento/?week_start=YYYY-MM-DD
```

`fid` is `AreaForca.fid`. `week_start` is required. The endpoint always compares the 7-day window `[week_start, week_start + 6]` against the prior 7 days `[week_start - 7, week_start - 1]`. Dates outside `[2000-01-01, today]` get `400`. Unknown `fid` gets `404`.

Response:

```jsonc
{
  "region": {
    "fid": 3,
    "name": "Lapa – Centro",
    "aisp": "AISP 5"
  },
  "week": {
    "start": "2024-05-13",
    "end":   "2024-05-19",
    "label": "13–19 mai"          // pre-formatted for header convenience
  },
  "verdict": "melhora",            // "melhora" | "estavel" | "piora"
  "deltas": [
    {
      "key":  "roubos_transeunte",
      "label": "Roubos a transeunte",
      "before": 42,
      "after":  30,
      "pct_change": -28.6,
      "positive": true,            // true when the change is good for the region
      "unit": "ocorrências"
    },
    {
      "key":  "disque_denuncia",
      "label": "Disque Denúncia",
      "before": 18,
      "after":  11,
      "pct_change": -38.9,
      "positive": true,
      "unit": "denúncias"
    },
    {
      "key":  "tempo_resposta",
      "label": "Tempo médio resposta",
      "before": null,              // see open question below
      "after":  null,
      "pct_change": null,
      "positive": null,
      "unit": "mm:ss"
    },
    {
      "key":  "cobertura_territorial",
      "label": "Cobertura territorial",
      "before": null,              // see open question below
      "after":  null,
      "pct_change": null,
      "positive": null,
      "unit": "%"
    }
  ],
  "actions": [
    {
      "id":    1,
      "title": "Reforço de patrulhamento a pé (24 agentes)",
      "completed_at": "2024-05-14",   // null when still pending
      "done":  true
    }
  ],
  "timeline": [
    {
      "ts":   "2024-05-13T08:00:00-03:00",
      "title": "Priorização aprovada",
      "detail": "score inicial 92"
    }
  ]
}
```

`pct_change` is a signed float (`(after - before) / before * 100`, rounded to one decimal). `null` means the metric has no data source yet — the frontend renders a dash in that card and skips the trend arrow.

Frontend-side cleanup that ships alongside this endpoint:

- Replace the `DELTAS` constant at `AvaliacaoView.tsx:18` with the response's `deltas` array. Map `before` / `after` to the current `prev` line ("42 → 30 ocorrências") on the client.
- Replace `CHECKLIST` (`:25`) with `actions`.
- Replace `TIMELINE` (`:33`) with `timeline`.
- Compute the trend arrow direction on the client from `pct_change` sign; backend ships only the number plus the `positive` boolean.

## Field-by-field mapping

| UI field | Source | Status |
| --- | --- | --- |
| `region.name` | `AreaForca.nome_subar` | exists |
| `region.aisp` | modal `Ocorrencia.aisp` inside polygon over current window — same rule as the regionlist endpoint | derivable, reuse helper |
| `week.label` | formatted on backend so the header doesn't need a locale-aware date lib on the client | new helper, trivial |
| `verdict` | derived from current-week vs prior-week `compute_scores` delta — thresholds suggested below | derive in backend |
| `deltas[].roubos_transeunte` | `Ocorrencia` filtered by polygon + `desc_delito` in the roubo-a-transeunte family + each 7-day window | derivable — needs canonical `desc_delito` list (same gap as the regionlist's `roubos_7d`) |
| `deltas[].disque_denuncia` | `DiskDenuncia` filtered by polygon + each 7-day window, optionally restricted to qualitative `classe` values | derivable — same `classe` policy decision as the regionlist's `disque_denuncia` |
| `deltas[].tempo_resposta` | **no source** — no response-time data in current models | **blocked** — see open questions |
| `deltas[].cobertura_territorial` | candidate sources: `Camera` density inside polygon (static), patrol assignment counts (no model), incident-to-response geographic coverage (no model) | **blocked** — see open questions |
| `actions` | analyst-authored playbook of weekly interventions, with completion timestamps | **blocked** — needs new `RegionAction` table + analyst write path |
| `timeline` | event log of priorização / deployment / operations / closure | **blocked** — needs new `RegionEvent` table + write hooks |

## Open questions to resolve before implementation

1. **Week boundary.** Confirm `week_start` is always a Monday by convention, or accept any date and treat it as day-0 of the 7-day window. Recommend the latter (simpler client) and document the convention.
2. **AISP labeling.** Same gap as the regionlist handoff — polygons can straddle multiple AISPs. Reuse whatever rule that endpoint adopts so headers don't disagree between tabs.
3. **`roubos_transeunte` / `disque_denuncia` definitions.** Same gap as the regionlist handoff. Whatever `desc_delito` list and `classe` policy gets decided there, reuse here.
4. **`verdict` thresholds.** Suggest:
   - `melhora` when the current-week score is at least 5 points below the prior week.
   - `piora` when it's at least 5 points above.
   - `estavel` otherwise.
   - Document the exact rule alongside `compute_scores` so the frontend doesn't need to know it.
5. **`tempo_resposta` source.** Either (a) drop the card from v1 (`deltas` returns 3 entries, frontend renders 3 cards), or (b) introduce a response-time ingest (likely from PMERJ / CICC). Recommend (a) for v1.
6. **`cobertura_territorial` definition.** Three candidates with very different semantics:
   - **Camera coverage** — fraction of polygon area within N metres of a `Camera`. Static (date window irrelevant).
   - **Patrol coverage** — needs patrol-assignment data; not modelled.
   - **Response coverage** — fraction of ocorrências within N metres of a unit at time-of-call; needs response-time data.
   For v1, recommend either dropping the card or returning camera coverage with a clear `unit: "% área coberta por câmera"` label.
7. **`actions` write path.** v1 options: (a) drop the section entirely; (b) introduce a `RegionAction` model + Django admin entry only (no public write API yet) so analysts can populate per-region weekly playbooks; (c) read from a hand-edited fixture. Recommend (b).
8. **`timeline` source.** Two candidates: (a) auto-generate from existing data (priorização event = the moment a region was added to the basket; closure event = the week boundary), (b) hand-authored via a `RegionEvent` model. Recommend a hybrid: auto-generate priorização + closure, allow analysts to insert ops events through admin.
9. **Pagination.** None expected — actions and timeline are small per week (~5 items each). Cap at 20 on the backend just in case.

## Suggested rollout

1. **v1 (unblocked work only).** Ship `GET /api/regions/{fid}/acompanhamento/` with:
   - `region`, `week`, `verdict` populated.
   - `deltas` containing `roubos_transeunte` and `disque_denuncia` only (the other two fully omitted, not returned with `null` — fewer surprises on the client).
   - `actions: []` and `timeline: []` empty arrays.
   Frontend hides the missing KPI cards, the actions section, and the timeline section when their arrays are empty (same pattern as the regionlist's `narrative` / `actions`).
2. **v1.1 — actions + timeline.** Once questions 7 and 8 are resolved, add the two models and admin CRUD; the response shape doesn't change.
3. **v2 — response time + coverage.** Once question 5 / 6 are resolved, add the remaining KPIs as additional `deltas` entries.

## Pointers

- Frontend mocks to retire: `AvaliacaoView.tsx:18` (`DELTAS`), `:25` (`CHECKLIST`), `:33` (`TIMELINE`).
- Score logic to reuse: `backend/ocorrencias/scoring.py` (`compute_scores`).
- Existing endpoint style to mirror: `AreaForcaScoreListView` in `backend/ocorrencias/views.py` (single-region drill-down should follow the same DRF `APIView` pattern with a query-param serializer).
- Routing entry point: `backend/config/urls.py` — add a `regions/<int:fid>/acompanhamento/` route. Consider grouping under the same `/api/regions/` prefix as the (planned) regionlist endpoint.
