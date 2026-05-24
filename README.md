# claude-hackaton-security

## How to run

You need [Docker](https://docs.docker.com/engine/install/) +
[Docker Compose v2](https://docs.docker.com/compose/install/). Three commands:

```bash
cp .env.example .env                                                   # 1. defaults work as-is
docker compose up --build                                              # 2. db + backend + frontend
docker compose exec backend python manage.py load_data --truncate      # 3. import the data (~30s)
```

Then:

- API — <http://localhost:8000>
- Frontend — <http://localhost:3000>
- Admin — <http://localhost:8000/admin/> (run
  `docker compose exec backend python manage.py createsuperuser` first)

Schema migrations run automatically every time the `backend` container
starts. Stop everything with `Ctrl+C` (or `docker compose down`).

For non-Docker setup, manual configuration, the API reference, and
troubleshooting, keep reading.

## About

Geospatial backend + frontend for analysing public-safety data in the city of
Rio de Janeiro. The frontend lets the user draw a region on a map and pick a
date window; the backend returns the crime occurrences, citizen denúncias,
camera coverage and urban risk factors that fall inside.

- **Backend** — Django 6 + Django REST Framework + GeoDjango on top of
  PostgreSQL/PostGIS.
- **Frontend** — Next.js 16 + MapLibre GL.
- **Data** — five CSVs + a shapefile in `data/`, sourced from the
  `claude_impact_lab_compstat_rio` reference repo. Four CSVs
  (`df_ocorrencias_tratado`, `cameras_areas_fm`, `disk_denuncia`,
  `fatores_urbanos`) and the `sh_area_forca` shapefile (municipal "áreas de
  força" — priority public-safety polygons) are imported into Postgres by a
  single management command.

## Project layout

```
.
├── backend/             Django project (config + ocorrencias app)
│   ├── config/          settings.py, urls.py, wsgi.py
│   └── ocorrencias/     models, serializers, views, loaders.py, tests
├── frontend/            Next.js app (MapLibre map UI)
├── data/                Source CSVs + shapefiles (not committed in full)
├── docker-compose.yml   db + backend + frontend
├── pyproject.toml       Python deps (managed by uv)
└── .env.example         Copy to .env and edit for local dev
```

## Prerequisites

You need **either** Docker Compose (easiest, recommended) **or** the manual
toolchain (uv + Node.js + a local Postgres with PostGIS).

| Tool | Why | Install |
| --- | --- | --- |
| Docker Engine | Run the stack in containers | <https://docs.docker.com/engine/install/> |
| Docker Compose v2 | `docker compose` subcommand | <https://docs.docker.com/compose/install/> |
| uv | Python dependency manager | <https://docs.astral.sh/uv/getting-started/installation/> |
| Node.js ≥ 20 + pnpm | Frontend build/dev | <https://nodejs.org/> · `corepack enable && corepack prepare pnpm@8 --activate` |
| PostgreSQL ≥ 14 + PostGIS ≥ 3 | If you skip Docker | <https://postgis.net/install/> |

> If you don't have Docker yet, follow the **Docker Engine** link first, then
> the **Docker Compose** link — Compose is shipped as a plugin to the modern
> Docker Engine on Linux, and bundled with Docker Desktop on macOS/Windows.

## 1. Configure environment

```bash
cp .env.example .env
```

Edit `.env` if you need to change ports or credentials. The defaults work
out of the box for local development:

```
DJANGO_SECRET_KEY=dev-insecure-key-change-me
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,0.0.0.0
DB_NAME=hackaton
DB_USER=hackaton
DB_PASS=hackaton
DB_HOST=127.0.0.1     # use "db" when running everything in docker compose
DB_PORT=5432
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173
```

## 2. Run the stack

### Option A — With Docker Compose (recommended)

One command brings up Postgres+PostGIS, the Django backend, and the Next.js
frontend:

```bash
docker compose up --build
```

That starts:

- **db** — `postgis/postgis:16-3.4` on `localhost:5432`
- **backend** — Django on <http://localhost:8000> (migrations run
  automatically on container start)
- **frontend** — Next.js on <http://localhost:3000>

Stop everything with `Ctrl+C` (or `docker compose down`).

To detach: `docker compose up --build -d`. Tail logs with
`docker compose logs -f backend`.

## 3. Load the data

The four CSVs and the `sh_area_forca` shapefile in `data/` are imported by a
single Django management command:

```bash
# Docker:
docker compose exec backend python manage.py load_data

# Manual:
cd backend && uv run python manage.py load_data
```

The command loads everything in declared order (ocorrencias → cameras →
disk_denuncia → fatores_urbanos → areas_forca). Useful flags:

```bash
# Wipe each table before loading
python manage.py load_data --truncate

# Just one or two datasets
python manage.py load_data --only cameras,fatores_urbanos

# Just the priority-zone polygons
python manage.py load_data --only areas_forca

# Small slice for a quick smoke test
python manage.py load_data --limit 1000

# Files in a non-default location
python manage.py load_data --data-dir /absolute/path/to/data
```

Available datasets: `ocorrencias`, `cameras`, `disk_denuncia`,
`fatores_urbanos`, `areas_forca`. Missing files are skipped with a warning
rather than aborting the whole run.

After loading you should see roughly:

| Dataset | Rows |
| --- | --- |
| ocorrencias | ~115,000 |
| cameras | 985 |
| disk_denuncia | ~18,000 parent rows |
| fatores_urbanos | ~2,085 |
| areas_forca | 8 polygons |

## 4. Hit the API

### 4a. Polygon + date-range search — `POST /api/ocorrencias/search/`

```bash
curl -X POST http://localhost:8000/api/ocorrencias/search/ \
  -H 'Content-Type: application/json' \
  -d '{
    "polygon": [
      [-22.914, -43.197], [-22.914, -43.174],
      [-22.901, -43.174], [-22.901, -43.197],
      [-22.914, -43.197]
    ],
    "start_date": "2020-01-01",
    "end_date":   "2020-12-31",
    "page_size":  3
  }'
```

Response shape:

```json
{
  "summary":    { "total": 170, "by_desc_delito": [...], "by_month": [...], "by_aisp": [...] },
  "pagination": { "page": 1, "page_size": 3, "total": 170, "total_pages": 57 },
  "results":    [ { "id": "...", "lat": -22.905, "lng": -43.182, "data": "2020-02-26", ... } ]
}
```

Polygon points are `[lat, lng]` pairs; the ring is auto-closed if you omit
the duplicate final point. `page_size` is capped at 2000.

### 4b. Risk scores per área de força — `GET /api/areas-forca/scores/`

Returns one risk score (0–100) per priority-zone polygon, computed as a
weighted-by-crime-type density (`weighted_count / area_km²`) min-max
normalized across all polygons.

```bash
curl 'http://localhost:8000/api/areas-forca/scores/?start_date=2023-01-01&end_date=2024-12-31'
```

Query params are optional (defaults: `start_date=2000-01-01`,
`end_date=today`).

Response shape:

```json
{
  "date_range": { "start_date": "2023-01-01", "end_date": "2024-12-31" },
  "weights":    { "Roubo a transeunte": 1.0, "Roubo de aparelho celular": 0.8, "Roubo em coletivo": 1.2 },
  "results": [
    {
      "fid": 20,
      "nome_subar": "Presidente Vargas - Campo de Santana - Central do Brasil - Cinelândia",
      "area_km2": 1.348,
      "geometry": { "type": "Polygon", "coordinates": [...] },
      "occurrence_count": 18,
      "weighted_count": 17.4,
      "density": 12.91,
      "score": 100.0,
      "score_raw": 12.91,
      "by_desc_delito": [{ "desc_delito": "Roubo a transeunte", "count": 12 }, ...],
      "by_year":        [{ "year": 2023, "count": 9 }, { "year": 2024, "count": 9 }]
    },
    ...
  ]
}
```

Results are sorted by `score` descending. Crime-type weights live in
`backend/ocorrencias/scoring.py` (`CRIME_WEIGHTS`).

### 4c. Admin

The Django admin at <http://localhost:8000/admin/> works once you create a
superuser:

```bash
docker compose exec backend python manage.py createsuperuser
# or, manual:
cd backend && uv run python manage.py createsuperuser
```

All models — `Ocorrencia`, `Camera`, `DiskDenuncia`, `FatorUrbano`,
`AreaForca` — are registered with GeoDjango's `GISModelAdmin`, so polygons
and points render on an OpenLayers map.

## 5. Tests

```bash
# Docker:
docker compose exec backend pytest

# Manual:
cd backend && uv run pytest
```

Twenty-five tests cover:

- `tests/test_search.py` (5) — polygon hit/miss, invalid input, date-range
  validation, pagination.
- `tests/test_scoring.py` (8) — weighted-density math, min-max
  normalization edges (zero occurrences, ties), score ordering, date-window
  filtering, endpoint round-trip with GeoJSON output, and validation errors.
- `tests/test_loaders.py` (12) — date reconciliation from the redundant
  `ano`/`mes`/`data` CSV columns (typo'd years, month conflicts, fallback
  to day=1, invalid input).

## Troubleshooting

- **`could not connect to server` on backend startup** — Postgres isn't ready
  yet. With Compose the healthcheck handles this; manually, wait a few
  seconds after starting Postgres and verify `pg_isready -h 127.0.0.1`.
- **`extension "postgis" is not available`** — your Postgres install is
  missing PostGIS. Either use the `postgis/postgis:16-3.4` image (Compose
  does this for you) or install the system package (`postgresql-16-postgis-3`
  on Debian/Ubuntu).
- **`GDAL`/`GEOS` errors when running locally** — install the libs:
  `sudo apt install gdal-bin libgdal-dev libgeos-dev libproj-dev`
  (Debian/Ubuntu) or `brew install gdal geos proj` (macOS).
- **Frontend can't reach the API** — confirm `NEXT_PUBLIC_API_URL` points at
  the backend host (the Compose default is `http://localhost:8000`).
- **`DisallowedHost: Invalid HTTP_HOST header: '0.0.0.0:8000'`** — your
  browser is hitting `http://0.0.0.0:8000/` (the URL `runserver` prints) but
  `DJANGO_ALLOWED_HOSTS` doesn't list `0.0.0.0`. Either browse via
  `http://localhost:8000/` / `http://127.0.0.1:8000/`, or add `0.0.0.0` to
  the variable in your `.env` and `docker compose up -d backend` to apply.
