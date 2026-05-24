# Backend handoff — Region ranking list

Audience: backend dev wiring the `RegionList` component (right-hand panel of the Diagnóstico view) to real data. Today every field in that panel is hard-coded mock data from `frontend/lib/compstat/regions.ts`. This document spells out what the UI shows, what data points must come from the backend, and which of those already exist vs. need new work.

## Component recap

- File: `frontend/components/compstat/RegionList.tsx` (header + filter), `RegionItem.tsx` (each card).
- Each row is a **region** (an Área de Força). Collapsed view shows: rank, name, AISP, roubos, denuncias, score + level chip. Expanded view shows: a "why this score" narrative, 5 weighted criteria with progress bars, and a list of suggested actions.
- Selecting a region adds to the user's pre-meeting basket; total "agents allocated" is summed from each region's actions (regex on the cost string today — see `agentsFor()`).

The UI is driven by the `Region` shape in `frontend/lib/compstat/regions.ts`. Below we map each field to its backend source.

## What the backend already has

- `GET /api/areas-forca/scores/?start_date&end_date` → per-polygon score, weighted/raw counts, density, area, geometry, breakdown by `desc_delito` and by `year`. Implemented at `backend/ocorrencias/views.py:98`. Serializer at `backend/ocorrencias/serializers.py:90`.
- `POST /api/ocorrencias/search/` → polygon + date-range point search with `summary.by_desc_delito`, `by_month`, `by_aisp`.
- Models in `backend/ocorrencias/models.py`:
  - `AreaForca` (8 municipal polygons, has `nome_subar`, `area_km2`, `geometry`).
  - `Ocorrencia` (114k rows, has `aisp`, `risp`, `desc_delito`, `data`, `location`).
  - `DiskDenuncia` (18k denúncias, has `data_denuncia`, `classe`, `location`, `bairro_logradouro`).
  - `FatorUrbano` (2k urban-factor responses, has `tipo_ocorrencia_descricao`, `location`).
  - `Camera` (985 surveillance cameras).

So the score, geometry, occurrence count and crime breakdown per polygon already exist. The gap is: linking denúncias / fatores urbanos / actions / narrative / AISP / intel to the same polygon, and shaping it for the list view.

## Proposed endpoint

Add a single endpoint that returns everything the list needs in one request, scoped to the same date window the rest of the diagnóstico view uses:

```
GET /api/regions/?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD
```

Response:

```json
{
  "date_range": { "start_date": "...", "end_date": "..." },
  "results": [
    {
      "id": 3,
      "name": "Lapa – Centro",
      "aisp": "AISP 5",
      "score": 92,
      "level": "critico",
      "roubos": 42,
      "denuncias": 18,
      "ambiente": 78,
      "intel": "Alta",
      "criteria": [
        { "key": "roubos_7d",          "label": "Roubos a transeunte (7d)", "value": "42",    "pct": 88, "level": "critico" },
        { "key": "disque_denuncia",    "label": "Disque Denúncia",          "value": "18",    "pct": 74, "level": "alto" },
        { "key": "fatores_ambientais", "label": "Fatores ambientais",       "value": "7/20",  "pct": 65, "level": "medio" },
        { "key": "relints_ativos",     "label": "RELINTs ativos",           "value": "3",     "pct": 80, "level": "critico" },
        { "key": "historico_4s",       "label": "Histórico 4 semanas",      "value": "+22%",  "pct": 71, "level": "alto" }
      ],
      "narrative": "<strong>Convergência crítica:</strong> …",
      "actions": [
        { "kind": "pol", "title": "Patrulhamento a pé reforçado",   "desc": "+24 agentes · turnos noturnos sex/sáb", "agents": 24, "cost_label": "24 agentes" },
        { "kind": "amb", "title": "Reparo emergencial de iluminação", "desc": "R. do Lavradio + Arcos · prazo 48h",   "agents": 0,  "cost_label": "COMLURB" }
      ]
    }
  ]
}
```

Frontend-side cleanup that should ship alongside this endpoint:

- `Region.id` becomes `number` (the `AreaForca.fid`) instead of the current string slug. Update the type in `frontend/lib/compstat/regions.ts` and any `Set<string>` / `Map<string, …>` keyed by region id (e.g. `selected: ReadonlySet<string>` in `CompStat.tsx` / `RegionList.tsx` / `DiagnosticoView.tsx`).
- Drop UI-only fields from the wire (`icon`, `color` hex) — the frontend maps `level` → color and `kind` → icon. Keep them centralized in the frontend.
- Replace the regex-based `agentsFor()` with the explicit `actions[].agents` number from the API.

## Field-by-field mapping

| Frontend field | Type | Source | Status |
| --- | --- | --- | --- |
| `id` | int | `AreaForca.fid` | exists |
| `name` | string | `AreaForca.nome_subar` | exists |
| `aisp` | string `"AISP NN"` | dominant `Ocorrencia.aisp` inside the polygon (mode) | derivable from existing data |
| `score` | int 0–100 | `compute_scores(...).score` rounded | exists |
| `level` | enum `critico\|alto\|medio\|baixo` | derive from `score` thresholds (≥85 / ≥70 / ≥50 / else) | derive in backend so all clients agree |
| `roubos` | int | `Ocorrencia.desc_delito` matching roubo-a-transeunte family, last 7 days, inside polygon | derivable — need the canonical list of `desc_delito` values that count as "roubo a transeunte" |
| `denuncias` | int | `DiskDenuncia` inside polygon, last 7 days, optionally filtered to qualitative `classe` | derivable — need policy on which `classe` values count |
| `ambiente` | int 0–100 | normalized count / weighted score of `FatorUrbano` inside polygon | new — agree on normalization (count vs. weighted by `tipo_ocorrencia_descricao`) |
| `intel` | enum `Alta\|Média\|Baixa` | RELINT volume? Currently no data source | **blocked** — see open questions |
| `criteria` | 5 rows | one per signal feeding the score | new — see "Criteria contract" below |
| `narrative` | HTML string | analyst-authored or templated | **blocked** — see open questions |
| `actions` | list | analyst-authored playbook | **blocked** — see open questions |

### Criteria contract

The 5 progress bars expanded under each region must come from the backend so the numbers reconcile with the headline score. Suggested keys with their data sources:

1. `roubos_7d` — count of roubos-a-transeunte in the last 7 days inside the polygon (`Ocorrencia`). `value` = count, `pct` = percentile across all regions for that signal.
2. `disque_denuncia` — qualitative `DiskDenuncia` count last 7d (`DiskDenuncia`).
3. `fatores_ambientais` — `FatorUrbano` density. `value` formatted as `"<count>/20"` (or whatever cap the team agrees on).
4. `relints_ativos` — needs a RELINT data source. Out of scope until one exists; return `0` or omit.
5. `historico_4s` — % change vs. the previous 4-week window for the same polygon (`Ocorrencia`).

For each criterion: backend computes the raw value AND the `pct` (0–100) used to draw the bar. `level` is derived from `pct` in the same way as the headline `score`.

## Open questions to resolve before implementation

1. **AISP labeling.** A polygon can straddle multiple AISPs. Pick a rule (modal AISP / primary AISP from a join table) and document it.
2. **`intel` field.** Today this is `Alta | Média | Baixa` with no obvious data source. Either (a) drop it from the response and the UI, or (b) ingest a RELINT dataset and define how to bucket it. Recommend (a) for the first cut.
3. **Narrative.** Three options:
   - Drop it (returns `""`) until an analyst-authored source exists.
   - Render a templated string from the criteria values ("aumento de 22% em roubos coincide com X RELINTs…").
   - Pull from a new `RegionNarrative` table maintained out-of-band.
   Recommend the templated approach for v1; mark fields it can't fill as empty.
4. **Actions.** Currently 100% hand-authored. Two paths: (a) ship the endpoint without actions for v1 (UI hides the section if empty); (b) introduce a `RegionAction` table with a small CRUD surface for analysts. Recommend (a).
5. **Date window semantics.** The mock shows "7d" everywhere. Should the endpoint accept `?window=7d|28d|custom` or always honor `start_date/end_date`? Recommend honoring the caller's `start_date/end_date` and computing "7d" / "4-week comparison" criteria relative to `end_date`.
6. **Region universe.** The mock has 8 regions covering well-known neighborhoods (Lapa, Copacabana, Madureira…). The `AreaForca` table has 8 rows but they're "subáreas municipais" with `nome_subar` values that may not match those neighborhoods one-to-one. Confirm whether the list should be: all `AreaForca` rows, AISPs, or a curated subset.
7. **Pagination / filtering.** The list filters by level (Todas / Crítico / Alto) on the client today. Confirm whether the backend should accept those as query params or return everything and let the client filter.

## Suggested rollout

1. Resolve open questions 1, 2, 5, 6 — they unblock the simplest version of the endpoint.
2. Ship `GET /api/regions/` returning `id`, `name`, `aisp`, `score`, `level`, `roubos`, `denuncias`, `ambiente`, and `criteria` (without `relints_ativos`).
3. Frontend swaps `REGIONS` constant for a React Query call, removing the mock from `frontend/lib/compstat/regions.ts`.
4. Follow-up PR adds `narrative` (templated) and `actions` if/when content is sourced.

## Pointers

- Frontend mock to retire: `frontend/lib/compstat/regions.ts:36` (REGIONS constant), `agentsFor()` at line 240.
- Score logic to reuse: `backend/ocorrencias/scoring.py` (`compute_scores`).
- Existing similar endpoint to mirror in style: `AreaForcaScoreListView` in `backend/ocorrencias/views.py:98`.
- URL routing entry point: `backend/config/urls.py` (add a `regions/` include alongside the existing `ocorrencias` and `areas-forca` routes).
