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
    "ieso": timedelta(days=1),
    "oeb": timedelta(days=7),
}

FRESHNESS_QUERY: dict[str, str] = {
    "gridwatch": "SELECT epoch_ms(max(timestamp)) FROM raw.gridwatch_readings",
    "ieso": "SELECT epoch_ms(max(timestamp)) FROM raw.ieso_generation",
    "oeb": "SELECT epoch_ms(max(effective_date)) FROM raw.oeb_rates",
}


def is_fresh(source: str) -> bool:
    """Return True if the DB already has recent enough data for this source."""
    if source not in FRESHNESS_THRESHOLD:
        return False
    try:
        con = duckdb.connect(DB_PATH, read_only=True)
        result = con.execute(FRESHNESS_QUERY[source]).fetchone()
        con.close()
        if result and result[0] is not None:
            # Convert epoch milliseconds to datetime
            last_update = datetime.fromtimestamp(result[0] / 1000, tz=timezone.utc)
            age = datetime.now(timezone.utc) - last_update
            is_data_fresh = age < FRESHNESS_THRESHOLD[source]
            if is_data_fresh:
                print(f"✓ {source} data is fresh (age: {age}, threshold: {FRESHNESS_THRESHOLD[source]})")
            return is_data_fresh
    except Exception as e:
        print(f"⚠ Freshness check failed for {source}: {e}")
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
            print(f"⊘ Skipping {name} — data is less than {FRESHNESS_THRESHOLD[name]} old")
            continue
        print(f"→ Running {name} source")
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
