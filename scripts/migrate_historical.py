#!/usr/bin/env python3
"""One-time migration: load historical CSVs from ontario-grid-data into DuckDB.

Usage:
    python scripts/migrate_historical.py --data-dir /path/to/ontario-grid-data/data

Expects the original repo's data layout:
    data/clean/
    ├── ieso/hourly/          *.csv  (Date, Hour, Nuclear, Gas, ...)
    ├── gridwatch.ca/hourly/  *.csv  (timestamp, co2_intensity, ...)
    └── oeb/                  *.csv  (effective_date, rate_class, rate_cents_per_kwh)
"""
from __future__ import annotations

import argparse
from pathlib import Path

import duckdb
import pandas as pd

DB_PATH = "ontario_grid.duckdb"


def migrate_ieso(con: duckdb.DuckDBPyConnection, data_dir: Path) -> None:
    ieso_dir = data_dir / "clean" / "ieso" / "hourly"
    if not ieso_dir.exists():
        print(f"  Skipping IESO — directory not found: {ieso_dir}")
        return

    frames = []
    for f in sorted(ieso_dir.glob("*.csv")):
        df = pd.read_csv(f)
        df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_", regex=False)
        frames.append(df)

    if not frames:
        print("  No IESO CSV files found")
        return

    df = pd.concat(frames, ignore_index=True)
    df["timestamp"] = (
        pd.to_datetime(df["date"]) + pd.to_timedelta(df["hour"].astype(int) - 1, unit="h")
    ).dt.strftime("%Y-%m-%dT%H:00:00")
    df = df.drop_duplicates(subset=["timestamp"])

    con.execute("CREATE SCHEMA IF NOT EXISTS raw")
    con.execute(
        "CREATE TABLE IF NOT EXISTS raw.ieso_generation AS SELECT * FROM df WHERE 1=0"
    )
    con.execute("INSERT OR IGNORE INTO raw.ieso_generation SELECT * FROM df")
    print(f"  IESO: inserted {len(df):,} rows")


def migrate_gridwatch(con: duckdb.DuckDBPyConnection, data_dir: Path) -> None:
    gw_dir = data_dir / "clean" / "gridwatch.ca" / "hourly"
    if not gw_dir.exists():
        print(f"  Skipping gridwatch — directory not found: {gw_dir}")
        return

    frames = [pd.read_csv(f) for f in sorted(gw_dir.glob("*.csv"))]
    if not frames:
        print("  No gridwatch CSV files found")
        return

    df = pd.concat(frames, ignore_index=True)
    df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_", regex=False)
    df = df.drop_duplicates(subset=["timestamp"])

    con.execute("CREATE SCHEMA IF NOT EXISTS raw")
    con.execute(
        "CREATE TABLE IF NOT EXISTS raw.gridwatch_readings AS SELECT * FROM df WHERE 1=0"
    )
    con.execute("INSERT OR IGNORE INTO raw.gridwatch_readings SELECT * FROM df")
    print(f"  Gridwatch: inserted {len(df):,} rows")


def migrate_oeb(con: duckdb.DuckDBPyConnection, data_dir: Path) -> None:
    oeb_dir = data_dir / "clean" / "oeb"
    if not oeb_dir.exists():
        print(f"  Skipping OEB — directory not found: {oeb_dir}")
        return

    frames = [pd.read_csv(f) for f in sorted(oeb_dir.glob("*.csv"))]
    if not frames:
        print("  No OEB CSV files found")
        return

    df = pd.concat(frames, ignore_index=True)
    df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_", regex=False)
    df = df.drop_duplicates(subset=["effective_date", "rate_class"])

    con.execute("CREATE SCHEMA IF NOT EXISTS raw")
    con.execute(
        "CREATE TABLE IF NOT EXISTS raw.oeb_rates AS SELECT * FROM df WHERE 1=0"
    )
    con.execute("INSERT OR IGNORE INTO raw.oeb_rates SELECT * FROM df")
    print(f"  OEB: inserted {len(df):,} rows")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", required=True, type=Path, help="Path to ontario-grid-data/data/")
    parser.add_argument("--db", default=DB_PATH, help="Output DuckDB path")
    args = parser.parse_args()

    print(f"Migrating historical data from {args.data_dir} → {args.db}")
    con = duckdb.connect(args.db)
    migrate_ieso(con, args.data_dir)
    migrate_gridwatch(con, args.data_dir)
    migrate_oeb(con, args.data_dir)
    con.close()
    print("Done.")
