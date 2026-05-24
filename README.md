# TerritorI.A.

[Video de apresentaçao](https://drive.google.com/drive/folders/1QqMWTR7PxfxCDJf2UbKmQgBpXuTWT8Dh?usp=drive_link)

> ![NOTE]
> O vídeo de apresentação é apenas um mockup para visualização das funcionalidades, por favor explorem o site para interagirem com a UX atualizada.


O TerritoI.A.visa integrar a visualização de dados relacionados aos furtos no Rio de Janeiro em uma plataforma de diagnóstico e gerenciamento.
Unindo parâmetros de localização a uma perspectiva temporal, o objetivo do TerritorI.A. é centralizar a tomada de decisão do CompStat em um só aplicativo.

- Interpolação
- Diagnóstico
- Priorização
- Gerenciamento
- Previsão

# Objetivos

- Melhor visualização
- Diagnósticos e Insights automáticos
- Comparação automática entre diagnósticos
- Acompanhamento de diagnósticos anteriores

# FUNCIONALIDADES
## Página de Priorização

- Mapa interativo por áreas de prioridade e visualização de criminalidade em áreas adjacentes
- Ranking de Prioridade (automática e editável manualmente)
- correlacionando dados quantitativos e qualitativos [que hoje são desintegrados]
- ações sugeridas para cada órgão competente por região (automática e editável manualmente)
- ações sugeridas para distribuição de agentes
- Aviso de subnotificação (Alerta para regiões com discrepância entre BOs e denúncias com ações propostas específicas)
- Exportar relatório

## Página de Avaliação

- Métrica de variabilidade dos índices
- Visualização por semana (De acordo com a rotina da CompStat)
- Comparação dos mapas - antigo e atual
- Taxa de Resolução por Instituição

## Possíveis Novas Funcionalidades

- Implementação de mais parâmetros
- Integração com os aplicativos da CompStat/Prefeitura
- Enviar encaminhamentos diretamente para os órgãos competentes
- Previsões mais sofisticadas

## How to run

You need [Docker](https://docs.docker.com/engine/install/) +
[Docker Compose v2](https://docs.docker.com/compose/install/). Three commands:

```bash
cp .env.example .env                                          # defaults work as-is
docker compose up --build -d                                  # db + backend + frontend
docker compose exec backend python manage.py load_data        # import the data (~30s)
```

Then open <http://localhost:3000>.

- API — <http://localhost:8000>
- Frontend — <http://localhost:3000>

Schema migrations run automatically every time the `backend` container
starts. Stop everything with `docker compose down`.

To re-import from scratch, pass `--truncate`:

```bash
docker compose exec backend python manage.py load_data --truncate
```

## About

Geospatial backend + frontend for analysing public-safety data in the city of
Rio de Janeiro. The frontend lets the user draw a region on a map and pick a
date window; the backend returns the crime occurrences, citizen denúncias,
camera coverage and urban risk factors that fall inside.

- **Backend** — Django 6 + Django REST Framework + GeoDjango on top of
  PostgreSQL/PostGIS.
- **Frontend** — Next.js 16 + MapLibre GL.
- **Data** — five CSVs + a shapefile in `data/`, imported into Postgres by a
  single management command.

## Scorer

Each area gets a **score from 0 to 100** that tells you, at a glance, how
dangerous it is compared to the others on the map. Higher = worse. The
number is built in three steps:

**1. Count crimes inside the area — but not all crimes count the same.**
We focus on street robbery and we weight each type by how harmful it tends
to be:

| Crime type | Weight | Why |
| --- | --- | --- |
| Robbery on public transit (*Roubo em coletivo*) | 1.2 | A single event hits many victims at once |
| Robbery of a pedestrian (*Roubo a transeunte*) | 1.0 | Baseline |
| Cell-phone snatching (*Roubo de aparelho celular*) | 0.8 | Sub-type of street robbery, lower bodily-harm risk |
| Anything else | 1.0 | Default |

So if a polygon has 10 transit robberies and 5 phone snatchings, its
"weighted count" is `10 × 1.2 + 5 × 0.8 = 16`, not 15.

**2. Adjust for the size of the area.** A big neighborhood with lots of
crimes might still be safer *per square kilometer* than a small one with
fewer. To compare fairly, we divide the weighted count by the area's size
in km² — this gives us the **crime density**.

**3. Put every area on the same 0–100 scale.** Among the areas being
compared, the one with the highest density becomes **100**, the one with
the lowest becomes **0**, and every other area sits proportionally
between them.

That final number is the **score**. It is always **relative**: change the
date window or the set of areas and the same neighborhood can move up or
down, because what's being compared has changed. We then bucket the score
into four labels so it's easy to read at a glance:

| Label | Score |
| --- | --- |
| Crítico | ≥ 85 |
| Alto | ≥ 70 |
| Médio | ≥ 50 |
| Baixo | below 50 |

The weights and the math live in `backend/ocorrencias/scoring.py` if you
want to tweak them.
