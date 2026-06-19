#!/usr/bin/env python3
"""Export dbt mart tables from DuckDB to Parquet for the Observable dashboard."""
from __future__ import annotations

import argparse
from pathlib import Path

import duckdb

DB_PATH = "ontario_grid.duckdb"

EXPORTS = {
    "fct_grid_generation": "SELECT * FROM main_marts.fct_grid_generation ORDER BY hour",
    "fct_co2_intensity":   "SELECT * FROM main_marts.fct_co2_intensity ORDER BY hour",
    "stg_oeb_rates":       "SELECT * FROM main_staging.stg_oeb_rates ORDER BY effective_date",
}


def export(db_path: str, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(db_path, read_only=True)
    for name, query in EXPORTS.items():
        out = out_dir / f"{name}.parquet"
        con.execute(f"COPY ({query}) TO '{out}' (FORMAT PARQUET)")
        rows = con.execute(f"SELECT count(*) FROM ({query})").fetchone()[0]
        print(f"  {name}: {rows:,} rows → {out}")
    con.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default=DB_PATH)
    parser.add_argument("--out-dir", default="dashboard/src/data", type=Path)
    args = parser.parse_args()
    print(f"Exporting Parquet from {args.db} → {args.out_dir}")
    export(args.db, args.out_dir)
    print("Done.")
