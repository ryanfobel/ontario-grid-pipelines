#!/usr/bin/env python3
"""One-time migration: load historical data from ontario-grid-data into DuckDB.

Usage:
    python scripts/migrate_historical.py --data-dir /path/to/ontario-grid-data

Expected layout inside that directory:
    data/clean/
    ├── gridwatch.ca/hourly/summary.csv   fuel-type + CO2 + demand data
    ├── ieso.ca/hourly/output/            {year}.csv  — plant-level output
    └── oeb.ca/electricity/               {RateType}.csv  — one file per rate type

The IESO plant-level CSVs are aggregated to fuel types using the IESO daily
XML report (same method as the live dlt source).  Requires network access.
"""
from __future__ import annotations

import argparse
import io
import sys
import xml.etree.ElementTree as ET
from datetime import date, timedelta
from pathlib import Path

import duckdb
import pandas as pd
import requests

DB_PATH = "ontario_grid.duckdb"
XML_DAILY_URL = (
    "http://reports.ieso.ca/public/GenOutputCapability/PUB_GenOutputCapability_{date}.xml"
)
XML_NS = "{http://www.theIMO.com/schema}"

# Column mapping: old gridwatch summary.csv → dlt raw.gridwatch_readings schema
GRIDWATCH_COL_MAP = {
    "nuclear (MW)":             "nuclear_mw",
    "hydro (MW)":               "hydro_mw",
    "gas (MW)":                 "gas_mw",
    "wind (MW)":                "wind_mw",
    "biofuel (MW)":             "biofuel_mw",
    "solar (MW)":               "solar_mw",
    "nuclear (%)":              "nuclear_pct",
    "hydro (%)":                "hydro_pct",
    "gas (%)":                  "gas_pct",
    "wind (%)":                 "wind_pct",
    "biofuel (%)":              "biofuel_pct",
    "solar (%)":                "solar_pct",
    "Imports (MW)":             "imports_mw",
    "Exports (MW)":             "exports_mw",
    "Net Import/Exports (MW)":  "net_import_exports_mw",
    "Power Generated (MW)":     "power_generated_mw",
    "Ontario Demand (MW)":      "ontario_demand_mw",
    "Total Emissions (tonnes)": "total_emissions_tonnes",
    "CO2e Intensity (g/kWh)":  "co2e_intensity_gco2_per_kwh",
}

IESO_FUEL_COLS = ["nuclear", "gas", "hydro", "wind", "solar", "biofuel", "other", "total"]


# ── Plant→fuel mapping (shared with live dlt source) ─────────────────────

def get_plant_fuel_mapping() -> dict[str, str]:
    print("  Fetching plant→fuel mapping from IESO XML...")
    for days_back in range(1, 10):
        target = (date.today() - timedelta(days=days_back)).strftime("%Y%m%d")
        url = XML_DAILY_URL.format(date=target)
        try:
            r = requests.get(url, timeout=30)
            if r.ok:
                root = ET.fromstring(r.text)
                generators = (
                    root.find(f"{XML_NS}IMODocBody")
                    .find(f"{XML_NS}Generators")
                    .findall(f"{XML_NS}Generator")
                )
                mapping = {
                    gen.find(f"{XML_NS}GeneratorName").text.strip().upper():
                        gen.find(f"{XML_NS}FuelType").text.lower()
                    for gen in generators
                }
                print(f"  Got {len(mapping)} generators from {target}")
                return mapping
        except requests.RequestException:
            continue
    print("  Warning: XML fetch failed; using name inference only", file=sys.stderr)
    return {}


def infer_fuel_from_name(name: str) -> str:
    n = name.lower()
    if any(k in n for k in ("nuclear", "pickering", "darlington", "bruce")):
        return "nuclear"
    if "wind" in n:
        return "wind"
    if any(k in n for k in ("solar", " pv")):
        return "solar"
    if any(k in n for k in ("biofuel", "biomass", "bio fuel")):
        return "biofuel"
    if any(k in n for k in ("beck", "niagara falls", "hydro", "lac ", "chenaux",
                             "madawaska", "des joachims", "saunders", "arnprior",
                             "queenston", "ottawa river")):
        return "hydro"
    if any(k in n for k in ("gas", "cogen", "ccgt", "lennox", " gu ")):
        return "gas"
    return "other"


# ── Gridwatch ─────────────────────────────────────────────────────────────

def migrate_gridwatch(con: duckdb.DuckDBPyConnection, data_dir: Path) -> None:
    summary_file = data_dir / "clean" / "gridwatch.ca" / "hourly" / "summary.csv"
    if not summary_file.exists():
        print(f"  Skipping gridwatch — not found: {summary_file}")
        return

    df = pd.read_csv(summary_file, index_col=0)
    df.index.name = "timestamp"
    df.index = pd.to_datetime(df.index).dt.strftime("%Y-%m-%dT%H:%M:%S")

    df = df.rename(columns=GRIDWATCH_COL_MAP)
    # Keep only mapped columns (drop any extras)
    keep = [c for c in df.columns if c in GRIDWATCH_COL_MAP.values()]
    df = df[keep].reset_index()
    df = df.drop_duplicates(subset=["timestamp"])

    con.execute("CREATE SCHEMA IF NOT EXISTS raw")
    con.execute("""
        CREATE TABLE IF NOT EXISTS raw.gridwatch_readings AS
        SELECT * FROM df WHERE 1=0
    """)
    con.execute("""
        INSERT INTO raw.gridwatch_readings
        SELECT * FROM df
        WHERE timestamp NOT IN (SELECT timestamp FROM raw.gridwatch_readings)
    """)
    print(f"  gridwatch: {len(df):,} rows")


# ── IESO plant-level → fuel-type aggregation ──────────────────────────────

def migrate_ieso(con: duckdb.DuckDBPyConnection, data_dir: Path) -> None:
    ieso_dir = data_dir / "clean" / "ieso.ca" / "hourly" / "output"
    if not ieso_dir.exists():
        print(f"  Skipping IESO — not found: {ieso_dir}")
        return

    files = sorted(ieso_dir.glob("*.csv"))
    if not files:
        print("  IESO: no CSV files found")
        return

    mapping = get_plant_fuel_mapping()
    rows: list[dict] = []

    for f in files:
        print(f"  IESO: processing {f.name}")
        df = pd.read_csv(f, index_col=0, low_memory=False)
        # Index is ISO timestamps (saved with tz info)
        df.index = pd.to_datetime(df.index, utc=True).strftime("%Y-%m-%dT%H:%M:%S")
        df.columns = df.columns.str.strip()

        gen_cols = [c for c in df.columns if c != "TOTAL"]

        for ts, row in df.iterrows():
            fuel_totals: dict[str, float] = {k: 0.0 for k in IESO_FUEL_COLS if k != "total"}
            for gen in gen_cols:
                val = row.get(gen)
                if pd.isna(val):
                    continue
                fuel = mapping.get(gen.strip().upper()) or infer_fuel_from_name(gen)
                fuel_totals[fuel if fuel in fuel_totals else "other"] += float(val)

            total_val = row.get("TOTAL")
            total = float(total_val) if pd.notna(total_val) else sum(fuel_totals.values())
            rows.append({"timestamp": ts, **fuel_totals, "total": total})

    if not rows:
        print("  IESO: no rows to insert")
        return

    result = pd.DataFrame(rows).drop_duplicates(subset=["timestamp"])
    con.execute("CREATE SCHEMA IF NOT EXISTS raw")
    con.execute("""
        CREATE TABLE IF NOT EXISTS raw.ieso_generation AS
        SELECT * FROM result WHERE 1=0
    """)
    con.execute("""
        INSERT INTO raw.ieso_generation
        SELECT * FROM result
        WHERE timestamp NOT IN (SELECT timestamp FROM raw.ieso_generation)
    """)
    print(f"  IESO: {len(result):,} rows")


# ── OEB rates ─────────────────────────────────────────────────────────────

def migrate_oeb(con: duckdb.DuckDBPyConnection, data_dir: Path) -> None:
    oeb_dir = data_dir / "clean" / "oeb.ca" / "electricity"
    if not oeb_dir.exists():
        print(f"  Skipping OEB — not found: {oeb_dir}")
        return

    files = sorted(oeb_dir.glob("*.csv"))
    if not files:
        print("  OEB: no CSV files found")
        return

    rows: list[dict] = []
    for f in files:
        rate_type = f.stem
        df = pd.read_csv(f, index_col=0, parse_dates=True)
        df.index.name = "effective_date"

        for ts, row in df.iterrows():
            for col, val in row.items():
                rows.append({
                    "effective_date": ts.date().isoformat(),
                    "rate_type": rate_type,
                    "rate_column": str(col),
                    "value_cents_per_kwh": float(val) if pd.notna(val) else None,
                })

    if not rows:
        print("  OEB: no rows to insert")
        return

    result = pd.DataFrame(rows).drop_duplicates(
        subset=["effective_date", "rate_type", "rate_column"]
    )
    con.execute("CREATE SCHEMA IF NOT EXISTS raw")
    con.execute("""
        CREATE TABLE IF NOT EXISTS raw.oeb_rates AS
        SELECT * FROM result WHERE 1=0
    """)
    con.execute("""
        INSERT INTO raw.oeb_rates
        SELECT * FROM result
        WHERE (effective_date, rate_type, rate_column) NOT IN (
            SELECT effective_date, rate_type, rate_column FROM raw.oeb_rates
        )
    """)
    print(f"  OEB: {len(result):,} rows")


# ── Entry point ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--data-dir", required=True, type=Path,
        help="Root of ontario-grid-data repo (contains data/clean/...)",
    )
    parser.add_argument("--db", default=DB_PATH, help="Output DuckDB path")
    parser.add_argument(
        "--sources", nargs="*", choices=["gridwatch", "ieso", "oeb"],
        default=["gridwatch", "ieso", "oeb"],
        help="Which sources to migrate (default: all)",
    )
    args = parser.parse_args()

    print(f"Migrating historical data from {args.data_dir} → {args.db}")
    con = duckdb.connect(args.db)

    if "gridwatch" in args.sources:
        print("Gridwatch:")
        migrate_gridwatch(con, args.data_dir)

    if "ieso" in args.sources:
        print("IESO:")
        migrate_ieso(con, args.data_dir)

    if "oeb" in args.sources:
        print("OEB:")
        migrate_oeb(con, args.data_dir)

    con.close()
    print("Done.")
