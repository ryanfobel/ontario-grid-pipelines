# Project Instructions for AI Agents

This file provides instructions and context for AI coding agents working on this project.

<!-- BEGIN BEADS INTEGRATION v:1 profile:minimal hash:970c3bf2 -->
## Beads Issue Tracker

This project uses **bd (beads)** for issue tracking. Run `bd prime` to see full workflow context and commands.

### Quick Reference

```bash
bd ready              # Find available work
bd show <id>          # View issue details
bd update <id> --claim  # Claim work
bd close <id>         # Complete work
```

### Rules

- Use `bd` for ALL task tracking — do NOT use TodoWrite, TaskCreate, or markdown TODO lists
- Run `bd prime` for detailed command reference and session close protocol
- Use `bd remember` for persistent knowledge — do NOT use MEMORY.md files

**Architecture in one line:** issues live in a local Dolt DB; sync uses `refs/dolt/data` on your git remote; `.beads/issues.jsonl` is a passive export. See https://github.com/gastownhall/beads/blob/main/docs/SYNC_CONCEPTS.md for details and anti-patterns.

## Agent Context Profiles

The managed Beads block is task-tracking guidance, not permission to override repository, user, or orchestrator instructions.

- **Conservative (default)**: Use `bd` for task tracking. Do not run git commits, git pushes, or Dolt remote sync unless explicitly asked. At handoff, report changed files, validation, and suggested next commands.
- **Minimal**: Keep tool instruction files as pointers to `bd prime`; use the same conservative git policy unless active instructions say otherwise.
- **Team-maintainer**: Only when the repository explicitly opts in, agents may close beads, run quality gates, commit, and push as part of session close. A current "do not commit" or "do not push" instruction still wins.

## Session Completion

This protocol applies when ending a Beads implementation workflow. It is subordinate to explicit user, repository, and orchestrator instructions.

1. **File issues for remaining work** - Create beads for anything that needs follow-up
2. **Run quality gates** (if code changed) - Tests, linters, builds
3. **Update issue status** - Close finished work, update in-progress items
4. **Handle git/sync by active profile**:
   ```bash
   # Conservative/minimal/default: report status and proposed commands; wait for approval.
   git status

   # Team-maintainer opt-in only, unless current instructions forbid it:
   git pull --rebase
   bd dolt push
   git push
   git status
   ```
5. **Hand off** - Summarize changes, validation, issue status, and any blocked sync/commit/push step

**Critical rules:**
- Explicit user or orchestrator instructions override this Beads block.
- Do not commit or push without clear authority from the active profile or the current user request.
- If a required sync or push is blocked, stop and report the exact command and error.
<!-- END BEADS INTEGRATION -->


## Build & Test

```bash
# Install dependencies
pip install -e ".[dev]"

# Run all tests (35 unit tests, all offline/mocked)
python -m pytest tests/ -v

# Run the full pipeline (dlt extract + dbt transform)
python pipeline.py --sources ieso gridwatch oeb

# Run specific sources only
python pipeline.py --sources gridwatch --skip-dbt

# Full refresh (re-load all data)
python pipeline.py --sources ieso --full-refresh

# Migrate historical data from ontario-grid-data exports
python scripts/migrate_historical.py --sources gridwatch ieso oeb
```

## Architecture Overview

This repo is a migration from [ontario-grid-data](https://github.com/ryanfobel/ontario-grid-data) (CSV-commit pattern) to a proper pipeline:

```
Sources (dlt)          Storage       Transforms (dbt)
─────────────────      ───────────   ────────────────────────────
ieso/source.py    ──►  DuckDB        stg_ieso_generation
gridwatch/source.py──► (raw schema)  stg_gridwatch
oeb/source.py     ──►               stg_oeb_rates
                                     fct_co2_intensity (mart)
```

**Data sources:**
- **IESO fuel mix** — Monthly CSVs from ieso.ca (2019-05+). Pre-2019 backfill via GOC annual Excel files.
- **Gridwatch** — Live Ontario grid scraper at `live.gridwatch.ca` using Selenium/Chrome headless.
- **OEB rates** — Historical electricity rate tables from oeb.ca via BeautifulSoup HTML parsing.

**Storage:** Single `ontario_grid.duckdb` file. Persisted across CI runs on an orphan `data` branch (single-commit force-push, no history accumulation).

**IP blocking:** All `*.ieso.ca` and `oeb.ca` endpoints return 403 from datacenter IPs (including this Claude Code environment). Both sources handle this gracefully (warn + skip). They work normally from GitHub Actions.

**dlt write disposition:** All resources use `merge` + `primary_key` for idempotent upserts.

## Conventions & Patterns

- **dlt resources** live in `pipelines/<source>/source.py`, decorated with `@dlt.resource(write_disposition="merge", primary_key=...)`
- **dbt models** in `transform/models/staging/` (views) and `transform/models/marts/` (tables)
- **OEB rates** stored in long format: `(effective_date, rate_type, rate_column, value_cents_per_kwh)`
- **IESO timestamps** are hour-ending in source, converted to hour-starting ISO 8601 (`HOUR=1` → `T00:00:00`)
- **Tests** mock all HTTP calls; never make real network requests in tests
- **Fuel columns:** `["nuclear", "gas", "hydro", "wind", "solar", "biofuel", "other", "total"]`
- **bd** (beads) is used for all task tracking — do not create TODO lists or markdown task files
