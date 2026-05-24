# Frontend handoff — Region ranking list

Audience: frontend dev wiring `RegionList` to the new `GET /api/regions/` endpoint. The backend half of this work is shipped (see `docs/backend-handoff-regionlist.md`). This doc tells you exactly what the endpoint returns, what to change in the frontend, and what to leave alone.

## What's live on the backend

`GET /api/regions/?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD`

Both query params are **required**. Dates outside `[2000-01-01, today]` or with `start_date > end_date` get `400`.

Returns one entry per `AreaForca` polygon (8 today), sorted by `score` desc:

```json
{
  "date_range": { "start_date": "2024-01-01", "end_date": "2024-12-31" },
  "results": [
    {
      "id": 20,
      "name": "Presidente Vargas - Campo de Santana - Central do Brasil - Cinelândia",
      "aisp": "AISP 5",
      "score": 100,
      "level": "critico",
      "roubos": 10,
      "denuncias": 0,
      "ambiente": 35,
      "criteria": [
        { "key": "roubos_7d",          "label": "Roubos a transeunte (7d)", "value": "10",   "pct": 90, "level": "critico" },
        { "key": "disque_denuncia",    "label": "Disque Denúncia",          "value": "0",    "pct": 0,  "level": "baixo"   },
        { "key": "fatores_ambientais", "label": "Fatores ambientais",       "value": "7/20", "pct": 35, "level": "baixo"   },
        { "key": "relints_ativos",     "label": "RELINTs ativos",           "value": "0",    "pct": 0,  "level": "baixo"   },
        { "key": "historico_4s",       "label": "Histórico 4 semanas",      "value": "+26%", "pct": 76, "level": "alto"    }
      ],
      "narrative": "",
      "actions": []
    }
  ]
}
```

### Field semantics (so you don't re-read the backend)

| Field | Notes |
| --- | --- |
| `id` | `AreaForca.fid`, an **integer**. Today's frontend `Region.id` is a string slug — see migration below. |
| `name` | `AreaForca.nome_subar`. These are subárea names, not the marketing names in the mock ("Lapa – Centro" etc). Don't relabel them on the client. |
| `aisp` | Modal `Ocorrencia.aisp` inside the polygon for the caller's window. **Empty string `""`** when the polygon has no occurrences in the window — render a dash or hide the chip. |
| `score` | Integer 0–100 from `compute_scores` (cross-region min-max of weighted density). |
| `level` | `"critico" \| "alto" \| "medio" \| "baixo"` derived from `score`: ≥85 / ≥70 / ≥50 / else. Trust this; don't recompute on the client. |
| `roubos`, `denuncias` | Counts inside polygon over **last 7d ending at `end_date`**, regardless of caller window. |
| `ambiente` | `FatorUrbano` count clamped to 20, scaled 0–100. |
| `criteria` | Always 5 items, in fixed order, with stable `key`. Use `key` (not array index) when rendering. `relints_ativos` is currently a stub (`value: "0"`, `pct: 0`) — see "Empty states" below. |
| `narrative` | Empty string in v1. UI should hide the "why this score" section when it's `""`. |
| `actions` | Empty array in v1. UI should hide the actions section and the "agents allocated" footer math when there are no actions across the basket. |

## Frontend changes to ship

The whole point of this endpoint is to retire `frontend/lib/compstat/regions.ts` mocks. Concretely:

### 1. New API client — `frontend/lib/api/regions.ts`

Mirror `frontend/lib/api/areas-forca.ts`:

```ts
import { API_BASE_URL } from "./ocorrencias"

export type RegionLevel = "critico" | "alto" | "medio" | "baixo"

export type RegionCriterion = {
  key: "roubos_7d" | "disque_denuncia" | "fatores_ambientais" | "relints_ativos" | "historico_4s"
  label: string
  value: string
  pct: number
  level: RegionLevel
}

export type RegionAction = {
  kind: "amb" | "pol" | "int"
  title: string
  desc: string
  agents: number
  cost_label: string
}

export type Region = {
  id: number
  name: string
  aisp: string
  score: number
  level: RegionLevel
  roubos: number
  denuncias: number
  ambiente: number
  criteria: RegionCriterion[]
  narrative: string
  actions: RegionAction[]
}

export type RegionsResponse = {
  date_range: { start_date: string; end_date: string }
  results: Region[]
}

export async function fetchRegions(
  startDate: string,
  endDate: string,
  signal?: AbortSignal,
): Promise<RegionsResponse> {
  const url = `${API_BASE_URL}/api/regions/?start_date=${encodeURIComponent(
    startDate,
  )}&end_date=${encodeURIComponent(endDate)}`
  const res = await fetch(url, { signal })
  if (!res.ok) {
    const text = await res.text().catch(() => "")
    throw new Error(
      `regions failed: ${res.status} ${res.statusText}${
        text ? ` — ${text.slice(0, 200)}` : ""
      }`,
    )
  }
  return (await res.json()) as RegionsResponse
}
```

Note `RegionAction` reflects the **wire shape** the backend returns *when* actions exist (`kind`, `agents`, `cost_label`). Even though v1 returns `actions: []`, type it correctly so we don't have to rewire later.

### 2. Wire React Query — `DiagnosticoView.tsx` (or a small `useRegions` hook)

Pattern matches `AreasLayer.tsx` already in the repo:

```ts
const { data, isLoading } = useQuery<RegionsResponse>({
  queryKey: ["regions", startDate, endDate],
  queryFn: ({ signal }) => fetchRegions(startDate, endDate, signal),
})
const regions = data?.results ?? []
```

`startDate` / `endDate` come from the same source that already drives `AreasLayer` and `useOcorrencias`. Do not pass an empty/default window — wait for the parent to provide real dates so we don't fire a redundant request.

### 3. Retire the mock

- Delete `REGIONS` (and the per-region hand-authored entries) from `frontend/lib/compstat/regions.ts:36`.
- Delete `agentsFor()` at `frontend/lib/compstat/regions.ts:240` — replace its single caller in `CompStat.tsx` with `regions.reduce((sum, r) => sum + r.actions.reduce((s, a) => s + a.agents, 0), 0)`.
- Move `LEVEL_COLOR` and `LEVEL_LABEL` (still UI-only) to a new `frontend/lib/compstat/levels.ts` (or keep them in `regions.ts` as long as you also delete the mock data and the `Region` type — but the cleanest split is "types/constants here, data fetched there").
- Keep the criterion-icon and action-icon maps on the client. The wire ships `kind` (for actions) and `key` (for criteria); the client maps them to icons. The backend deliberately does **not** send `icon` strings or `color` hex.

### 4. Switch region ids from `string` → `number`

This is the change with the most surface area. Today the slug `"lapa"` flows through several places typed as `string`. The wire `id` is an integer. Update:

- `Region.id: number` (done in the new `frontend/lib/api/regions.ts`).
- `frontend/components/compstat/CompStat.tsx:44` — `useState<ReadonlySet<string>>` → `ReadonlySet<number>`. Same at `:67`.
- `frontend/components/compstat/DiagnosticoView.tsx:22` (`selected: ReadonlySet<string>`), `:39` (`openId: string | null`) — both become `number`.
- `frontend/components/compstat/RegionList.tsx:13-16` — `selected: ReadonlySet<number>`, `openId: number | null`, `onToggleOpen: (id: number) => void`, `onToggleSelect: (id: number) => void`.
- `frontend/components/compstat/RegionItem.tsx:15-16` — same callback signature change.

There are no `Map<string, …>` keyed by region id today (grepped). If you add one, key it by `number`.

## UI behaviors to honor

These keep the UI sensible during the v1 cut where some fields are intentionally empty:

- **Empty `narrative`** → hide the "why this score" block entirely; don't render an empty `<strong>`.
- **Empty `actions`** → hide the actions section and zero out the "agents allocated" footer (it should already read 0 once `agentsFor` is replaced).
- **`relints_ativos` stub** → render it like any other criterion. It will always read `0` / `pct: 0` / `level: "baixo"` until a RELINT data source exists. Don't special-case it now.
- **Empty `aisp`** → render a dash (`"—"`) or hide the chip; don't render the literal `"AISP "` string.
- **All zeros in the window** → if the caller passes a date range with no data (e.g. future dates), every region returns `score: 0`, `level: "baixo"`, empty `aisp`. UI should still render the rows; the level filter can leave the list empty without an error state.

## What NOT to change

- Don't recompute `level` thresholds on the client. The backend owns them so the map color and the list color stay in sync.
- Don't filter on the client by `level` and re-call the API on the change. The list filter (Todas / Crítico / Alto) keeps working as a pure client-side filter on the same fetched array.
- Don't sort. Backend returns sorted by `score` desc; preserve that order.
- Don't try to derive `roubos` / `denuncias` from the existing `/api/area-snapshot/` or `/api/ocorrencias/search/` responses. They use the caller's window, not the fixed 7-day window the criteria need. Trust `/api/regions/` for these numbers and only use the other endpoints for their own concerns (map points, drill-downs).

## Testing checklist

- [ ] Loading state: skeleton or spinner while React Query is pending; no flicker of an empty list.
- [ ] Error state: API down or 400 surfaces a visible error (the existing `Toast` is fine).
- [ ] Date-window change: switching the diagnóstico date range refetches and re-renders the list (queryKey already includes the dates).
- [ ] Selection survives refetch: `selected: ReadonlySet<number>` keeps user picks across a date change as long as the same `fid`s exist (they will — only 8 polygons today).
- [ ] Level filter still works: filtering to "Crítico" only shows `level === "critico"` rows.
- [ ] No console warnings about `key` props or type mismatches after the `string → number` id migration.

## Follow-ups (not in this PR)

These are queued for when content/data sources exist; the API shape already supports them so no further wire changes are needed:

- `narrative`: backend will populate a templated string. UI just stops hiding the section when it's non-empty.
- `actions`: backend will return `RegionAction[]`. UI re-shows the actions section and the agents footer math just works because of the new `actions[].agents` field.
- `relints_ativos`: stays in the criteria array; only its `value` / `pct` / `level` will start changing once a RELINT source is ingested.

## Pointers

- New API client to add: `frontend/lib/api/regions.ts` (mirror `frontend/lib/api/areas-forca.ts:1`).
- Mock to retire: `frontend/lib/compstat/regions.ts:36` (REGIONS), `frontend/lib/compstat/regions.ts:240` (agentsFor).
- Type/id ripple: `CompStat.tsx:44`, `DiagnosticoView.tsx:22`/`:39`, `RegionList.tsx:13-16`, `RegionItem.tsx:15-16`.
- Existing useQuery pattern to mirror: `frontend/components/map/AreasLayer.tsx:62`.
