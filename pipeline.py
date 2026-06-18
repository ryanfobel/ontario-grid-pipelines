#!/usr/bin/env python3
"""Ontario grid data pipeline — orchestrates dlt extraction and dbt transforms."""
import argparse
import subprocess

import dlt

from pipelines.gridwatch import gridwatch_source
from pipelines.ieso import ieso_source
from pipelines.oeb import oeb_source

DB_PATH = "ontario_grid.duckdb"
ALL_SOURCES = ["ieso", "gridwatch", "oeb"]


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
        load_info = pipeline.run(source_map[name](), write_disposition=disposition)
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
