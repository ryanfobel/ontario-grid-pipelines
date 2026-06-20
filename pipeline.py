#!/usr/bin/env python3
"""Ontario grid data pipeline — orchestrates dlt extraction and dbt transforms."""
import argparse
import subprocess
from datetime import datetime, timezone, timedelta

import dlt
import duckdb

from pipelines.gridwatch import gridwatch_source
from pipelines.ieso import ieso_source
from pipelines.oeb import oeb_source

DB_PATH = "ontario_grid.duckdb"
ALL_SOURCES = ["ieso", "gridwatch", "oeb"]


FRESHNESS_THRESHOLD: dict[str, timedelta] = {
    "gridwatch": timedelta(hours=1),
}

FRESHNESS_QUERY: dict[str, str] = {
    "gridwatch": "SELECT max(timestamp) FROM raw.gridwatch_readings",
}


def is_fresh(source: str) -> bool:
    """Return True if the DB already has recent enough data for this source."""
    if source not in FRESHNESS_THRESHOLD:
        return False
    try:
        con = duckdb.connect(DB_PATH, read_only=True)
        result = con.execute(FRESHNESS_QUERY[source]).fetchone()
        con.close()
        if result and result[0]:
            age = datetime.now(timezone.utc) - result[0].replace(tzinfo=timezone.utc)
            return age < FRESHNESS_THRESHOLD[source]
    except Exception:
        pass
    return False


def run_dlt(sources: list[str], full_refresh: bool = False) -> None:
    pipeline = dlt.pipeline(
        pipeline_name="ontario_grid",
        destination=dlt.destinations.duckdb(DB_PATH),
        dataset_name="raw",
    )
    disposition = "replace" if full_refresh else "merge"

    source_map = {
        "ieso": ieso_source,
        "gridwatch": gridwatch_source,
        "oeb": oeb_source,
    }
    for name in sources:
        if not full_refresh and is_fresh(name):
            print(f"Skipping {name} — data is less than {FRESHNESS_THRESHOLD[name]} old")
            continue
        source = source_map[name]()
        # Freeze schema: unexpected new columns or data types raise an error
        # rather than silently altering the table. Evolve intentionally.
        source.schema_contract = {"columns": "freeze", "data_type": "freeze"}
        load_info = pipeline.run(source, write_disposition=disposition)
        print(load_info)


def run_dbt() -> None:
    subprocess.run(
        ["dbt", "run", "--project-dir", "transform", "--profiles-dir", "transform"],
        check=True,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ontario grid data pipeline")
    parser.add_argument(
        "--sources",
        nargs="*",
        choices=ALL_SOURCES,
        default=ALL_SOURCES,
        help="Which sources to run (default: all)",
    )
    parser.add_argument("--full-refresh", action="store_true", help="Replace all data")
    parser.add_argument("--skip-dbt", action="store_true", help="Skip dbt transforms")
    args = parser.parse_args()

    run_dlt(args.sources, args.full_refresh)
    if not args.skip_dbt:
        run_dbt()
