# Frontend Data Fetching — Áreas de Força + Per-Area Snapshot

Audience: the frontend agent wiring the map UI to the backend. This doc covers the two NEW endpoints added in PR #3 (`feat/area-snapshot-endpoints`). For the older "region ranking list" handoff see [`docs/backend-handoff-regionlist.md`](../docs/backend-handoff-regionlist.md) — that work is separate.

## The two-query flow

The whole UI loop is two API calls:

1. **First query** — fetch all áreas de força (polygons + ids) to draw them on the map.
   ```
   GET /api/areas-forca/
   ```
2. **Second query** — when an area is selected/clicked, send its `fid` (plus a date range) and the backend returns every dataset filtered to that area.
   ```
   POST /api/area-snapshot/
   ```

Repeat step 2 once per area the user wants to inspect. There is no aggregated "all areas at once" endpoint — call step 2 per fid as needed.

---

## 1. `GET /api/areas-forca/`

Returns a **GeoJSON FeatureCollection** of every área de força. The shape is identical to the static `/data/areas-forca.geojson` the existing `AreasLayer.tsx` already consumes, so the swap is just replacing the URL.

**Request:** no body, no query params.

**Response:**

```jsonc
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "geometry": {
        "type": "Polygon",
        "coordinates": [[[lng, lat], [lng, lat], ...]]
      },
      "properties": {
        "fid": 2,
        "nome_subar": "Rodoviária - Terminal Gentileza - Estação Leopoldina",
        "area_km2": 0.872
      }
    },
    // ... 8 features total
  ]
}
```

**Key field for the second query:** `feature.properties.fid` (integer). Pass this back as the `fid` field in `/api/area-snapshot/`.

**Frontend integration point.** In `frontend/components/map/AreasLayer.tsx`:

```ts
// before
const res = await fetch(AREAS_GEOJSON_URL)               // "/data/areas-forca.geojson"

// after
const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/areas-forca/`)
```

The `AreasProperties` type already declares `fid: number` and `nome_subar: string`; `area_km2: number` can be appended.

---

## 2. `POST /api/area-snapshot/`

Returns all data inside a single área de força for a given date range.

**Request body:**

```jsonc
{
  "fid": 2,                       // integer, must match an existing area_forca row
  "start_date": "2023-01-01",     // YYYY-MM-DD
  "end_date":   "2023-12-31"      // YYYY-MM-DD
}
```

**Response (200):**

```jsonc
{
  "area_forca": {
    "fid": 2,
    "nome_subar": "Rodoviária - Terminal Gentileza - Estação Leopoldina",
    "area_km2": 0.872
  },
  "ocorrencias": {
    "summary": {
      "total": 679,
      "truncated": false,
      "by_desc_delito": [
        { "desc_delito": "Roubo a transeunte", "count": 412 },
        // ...
      ]
    },
    "results": [
      {
        "id": "<id_criptografado>",
        "lat": -22.9032,
        "lng": -43.2105,
        "data": "2023-08-14",
        "desc_delito": "Roubo a transeunte",
        "aisp": 5,
        "risp": 1,
        "locf": "..."
      }
      // up to 5000 rows
    ]
  },
  "denuncias": {
    "summary": {
      "total": 33,
      "truncated": false,
      "by_classe": [
        { "classe": "SUBSTÂNCIAS ENTORPECENTES", "count": 21 },
        // ...
      ]
    },
    "results": [
      {
        "id": 2301680,
        "lat": -22.8996,
        "lng": -43.2014,
        "numero_denuncia": "1024.6.2020",
        "data_denuncia": "2020-06-04T08:16:00Z",
        "data_difusao": "2020-06-15T14:57:00Z",
        "bairro_logradouro": "SANTO CRISTO",
        "subbairro_logradouro": "",
        "municipio": "RIO DE JANEIRO",
        "estado": "RJ",
        "orgao_nome": "5 BPM",
        "orgao_tipo": "OPERACIONAL",
        "classe": "SUBSTÂNCIAS ENTORPECENTES",
        "tipo": "CONSUMO DE DROGAS",
        "status_denuncia": "",
        "relato_redacted": "..."
      }
    ]
  },
  "cameras": {
    "summary": { "total": 310, "truncated": false },
    "results": [
      {
        "id": "8f30106e-358f-4e8f-b94a-dc748e9624a9",
        "lat": -22.9094,
        "lng": -43.1802,
        "nome_area_fm": "Presidente Vargas - ...",
        "id_trecho": 203724
      }
    ]
  },
  "fatores_urbanos": {
    "summary": {
      "total": 50,
      "truncated": false,
      "by_tipo_ocorrencia": [
        { "tipo_ocorrencia_descricao": "Vegetação obstruindo a visibilidade do passeio", "count": 18 }
      ]
    },
    "results": [
      {
        "id": 732,
        "lat": -22.8916,
        "lng": -43.2743,
        "logradouro": "Rua Coração de Maria",
        "numero_porta": "426",
        "bairro_nome": "Meier",
        "subarea_nome": "Estação Méier - Cachambi",
        "tipo_ocorrencia_descricao": "Vegetação obstruindo a visibilidade do passeio",
        "orgao_responsavel": "COMLURB"
      }
    ]
  }
}
```

**Error responses:**

- `400 Bad Request` — invalid body (missing fields, `start_date > end_date`, dates outside `[2000-01-01, today]`).
- `404 Not Found` — `{ "detail": "area_forca with fid=<n> not found" }` when the supplied `fid` does not exist.

### Date filter scope

The date range is applied **only** to tables that have a date column:

| Dataset | Date column used for filtering |
| --- | --- |
| `ocorrencias` | `data` |
| `denuncias` | `data_denuncia` (date part — time component ignored) |
| `cameras` | none — returns all cameras inside the polygon |
| `fatores_urbanos` | none — returns all rows inside the polygon |

So shrinking the date window will only reduce `ocorrencias` and `denuncias`; the static reference layers stay constant for the same `fid`.

### Safety cap

Each `results` list is capped at **5000 rows** per dataset. When the cap is hit, `summary.truncated === true` and `summary.total` is still the real count. The summary aggregations (`by_desc_delito`, `by_classe`, `by_tipo_ocorrencia`) use the full unsliced queryset, so they always reflect the true totals even when results are truncated.

---

## Suggested frontend changes

1. **Drop the static GeoJSON file.** Replace the fetch in `frontend/components/map/AreasLayer.tsx` to call `GET /api/areas-forca/` instead of `/data/areas-forca.geojson`. The response shape is identical so the rest of that component (sources, layers, click popup) can stay.
2. **Add a click handler** on the áreas-forca fill layer that:
   - reads `feature.properties.fid`,
   - reads the current date range from `useSelectedWeek` (or whichever date hook the diagnóstico view uses),
   - calls `POST /api/area-snapshot/ { fid, start_date, end_date }`,
   - hands the response to whatever panel/state owns "selected area details".
3. **Typing.** Suggested TS shapes (illustrative — adjust to your conventions):

   ```ts
   type AreaForcaProperties = { fid: number; nome_subar: string; area_km2: number }
   type AreasFeatureCollection = GeoJSON.FeatureCollection<GeoJSON.Polygon, AreaForcaProperties>

   type SnapshotRequest = {
     fid: number
     start_date: string  // YYYY-MM-DD
     end_date:   string  // YYYY-MM-DD
   }

   type DatasetSummary<K extends string = never> = {
     total: number
     truncated: boolean
   } & { [P in K]?: Array<Record<string, unknown>> }

   type AreaSnapshotResponse = {
     area_forca: { fid: number; nome_subar: string; area_km2: number }
     ocorrencias: { summary: DatasetSummary<"by_desc_delito">, results: OcorrenciaRow[] }
     denuncias:   { summary: DatasetSummary<"by_classe">,      results: DenunciaRow[] }
     cameras:     { summary: DatasetSummary,                   results: CameraRow[] }
     fatores_urbanos: { summary: DatasetSummary<"by_tipo_ocorrencia">, results: FatorUrbanoRow[] }
   }
   ```

4. **Caching.** Areas are static — fetch `/api/areas-forca/` once at mount and cache. Snapshot responses are per-`(fid, start_date, end_date)` — a `useQuery` keyed on those three is a good fit.

---

## CORS / base URL

The backend already allows `http://localhost:3000` and `http://localhost:5173`. Use `process.env.NEXT_PUBLIC_API_URL` (set in `docker-compose.yml`) as the base.

```ts
const base = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"
fetch(`${base}/api/areas-forca/`)
```

---

## Where the backend code lives

- Views: `backend/ocorrencias/views.py` — `AreasForcaListView` and `AreaSnapshotView`.
- Serializers: `backend/ocorrencias/serializers.py` — `AreaForcaFeatureSerializer`, `AreaSnapshotRequestSerializer`, `CameraSerializer`, `FatorUrbanoSerializer`, `DiskDenunciaSerializer`.
- Routes: `backend/config/urls.py` mounts `/api/areas-forca/` and `/api/area-snapshot/`; route declarations live in `backend/ocorrencias/urls.py`.
- Tests covering both endpoints: `backend/tests/test_area_snapshot.py`.
