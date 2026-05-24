# claude-hackaton-security

Geospatial backend + frontend for analysing public-safety data in the city of
Rio de Janeiro. The frontend lets the user draw a region on a map and pick a
date window; the backend returns the crime occurrences, citizen denúncias,
camera coverage and urban risk factors that fall inside.

- **Backend** — Django 6 + Django REST Framework + GeoDjango on top of
  PostgreSQL/PostGIS.
- **Frontend** — Next.js 16 + MapLibre GL.
- **Data** — five CSVs + a shapefile in `data/`, sourced from the
  `claude_impact_lab_compstat_rio` reference repo. The four CSVs that drive
  the API (`df_ocorrencias_tratado`, `cameras_areas_fm`, `disk_denuncia`,
  `fatores_urbanos`) are imported into Postgres by a single management
  command.

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
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
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

### Option B — Without Docker (manual)

#### B1. Database

Install PostgreSQL and the PostGIS extension locally (see prerequisites table
above), then create the database:

```bash
sudo -u postgres psql <<SQL
CREATE USER hackaton WITH PASSWORD 'hackaton';
CREATE DATABASE hackaton OWNER hackaton;
\c hackaton
CREATE EXTENSION postgis;
SQL
```

Make sure `DB_HOST=127.0.0.1` in your `.env`.

#### B2. Backend

```bash
uv sync                              # install Python deps into .venv/
cd backend
uv run python manage.py migrate      # apply schema
uv run python manage.py runserver    # http://localhost:8000
```

#### B3. Frontend

```bash
cd frontend
pnpm install
pnpm dev                             # http://localhost:3000
```

## 3. Load the data

The four CSVs in `data/` are imported by a single Django management command:

```bash
# Docker:
docker compose exec backend python manage.py load_data

# Manual:
cd backend && uv run python manage.py load_data
```

The command loads everything in declared order (ocorrencias → cameras →
disk_denuncia → fatores_urbanos). Useful flags:

```bash
# Wipe each table before loading
python manage.py load_data --truncate

# Just one or two datasets
python manage.py load_data --only cameras,fatores_urbanos

# Small slice for a quick smoke test
python manage.py load_data --limit 1000

# CSVs in a non-default location
python manage.py load_data --data-dir /absolute/path/to/csvs
```

Available datasets: `ocorrencias`, `cameras`, `disk_denuncia`,
`fatores_urbanos`. Missing files are skipped with a warning rather than
aborting the whole run.

After loading you should see roughly:

| Dataset | Rows |
| --- | --- |
| ocorrencias | ~115,000 |
| cameras | 985 |
| disk_denuncia | ~18,000 parent rows |
| fatores_urbanos | ~2,085 |

## 4. Hit the API

The polygon + date-range search endpoint:

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

The Django admin at <http://localhost:8000/admin/> works once you create a
superuser:

```bash
docker compose exec backend python manage.py createsuperuser
# or, manual:
cd backend && uv run python manage.py createsuperuser
```

## 5. Tests

```bash
# Docker:
docker compose exec backend pytest

# Manual:
cd backend && uv run pytest
```

Six tests cover polygon hit/miss, invalid input, date-range validation,
null-date exclusion, and pagination.

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
