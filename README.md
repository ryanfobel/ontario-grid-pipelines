# ontario-grid-pipelines

dlt + dbt pipelines for Ontario electricity grid data. Replaces the CSV-commit
approach in [ontario-grid-data](https://github.com/ryanfobel/ontario-grid-data)
with a proper extraction layer (dlt) and transform layer (dbt), storing
everything in a single DuckDB file.

## Architecture

```
Sources                 Extract (dlt)          Store       Transform (dbt)
──────────────────────  ─────────────────────  ──────────  ───────────────
IESO fuel-mix CSV   ──► pipelines/ieso/     ──►           ──► staging/
gridwatch.ca        ──► pipelines/gridwatch/ ──► DuckDB   ──► marts/
OEB rates HTML      ──► pipelines/oeb/      ──►           ──► fct_*
```

The DuckDB file lives on an orphan `data` branch (single-commit force-push on
each CI run — no history accumulates).

## Quickstart

```bash
pip install -e .
python pipeline.py            # run all sources + dbt
python pipeline.py --sources ieso --skip-dbt   # one source only
python pipeline.py --full-refresh              # replace all data
```

## One-time historical migration

```bash
python scripts/migrate_historical.py \
  --data-dir /path/to/ontario-grid-data/data
```

## Project layout

```
pipelines/
├── ieso/       IESO hourly fuel-mix CSV (2019–present)
├── gridwatch/  gridwatch.ca Selenium scraper (CO2 intensity)
└── oeb/        OEB electricity rates HTML scraper

transform/
├── models/staging/   clean + cast raw dlt tables
└── models/marts/     fct_grid_generation, fct_co2_intensity

scripts/
└── migrate_historical.py   one-time CSV → DuckDB backfill

.github/workflows/pipeline.yml   daily CI + orphan data branch push
```

## Status

- [x] IESO fuel-mix source (incremental, CSV 2019+)
- [ ] gridwatch.ca source (port Selenium logic from ontario-grid-data)
- [ ] OEB rates source (port BeautifulSoup logic from ontario-grid-data)
- [ ] Pre-2019 IESO backfill (Excel files via migrate_historical.py)
