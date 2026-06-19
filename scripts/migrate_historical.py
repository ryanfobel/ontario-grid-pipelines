#!/usr/bin/env python3
"""One-time migration: load historical data from ontario-grid-data into DuckDB.

Fetches CSV files directly from the public ontario-grid-data GitHub repo.
No local checkout needed.

Usage:
    python scripts/migrate_historical.py
    python scripts/migrate_historical.py --sources gridwatch ieso oeb
    python scripts/migrate_historical.py --data-dir /path/to/ontario-grid-data  # local override
"""
from __future__ import annotations

import argparse
import io
import sys
import xml.etree.ElementTree as ET
from datetime import date, timedelta
from pathlib import Path
from urllib.parse import quote

import duckdb
import pandas as pd
import requests

DB_PATH = "ontario_grid.duckdb"
XML_DAILY_URL = (
    "http://reports.ieso.ca/public/GenOutputCapability/PUB_GenOutputCapability_{date}.xml"
)
XML_NS = "{http://www.theIMO.com/schema}"

RAW_BASE = "https://raw.githubusercontent.com/ryanfobel/ontario-grid-data/main/data/clean"
IESO_YEARS = list(range(2010, 2027))
OEB_RATE_FILES = [
    "Tiered rates.csv",
    "Time-of-Use (TOU) rates.csv",
    "Ultra-Low Overnight (ULO).csv",
]

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


def _fetch_csv(url: str) -> pd.DataFrame | None:
    try:
        r = requests.get(url, timeout=60)
        r.raise_for_status()
        return pd.read_csv(io.StringIO(r.text), index_col=0, low_memory=False)
    except requests.HTTPError as e:
        print(f"  Warning: {url} → {e}", file=sys.stderr)
        return None


# ── Plant→fuel mapping ────────────────────────────────────────────────────

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

def migrate_gridwatch(con: duckdb.DuckDBPyConnection, data_dir: Path | None) -> None:
    if data_dir:
        path = data_dir / "clean" / "gridwatch.ca" / "hourly" / "summary.csv"
        if not path.exists():
            print(f"  Skipping gridwatch — not found: {path}")
            return
        df = pd.read_csv(path, index_col=0)
    else:
        url = f"{RAW_BASE}/gridwatch.ca/hourly/summary.csv"
        print(f"  Fetching {url}")
        df = _fetch_csv(url)
        if df is None:
            return

    df.index.name = "timestamp"
    df.index = pd.to_datetime(df.index, utc=True).tz_localize(None).strftime("%Y-%m-%dT%H:%M:%S")
    df = df.rename(columns=GRIDWATCH_COL_MAP)
    keep = [c for c in df.columns if c in GRIDWATCH_COL_MAP.values()]
    df = df[keep].reset_index().drop_duplicates(subset=["timestamp"])

    con.execute("CREATE SCHEMA IF NOT EXISTS raw")
    con.execute("""
        CREATE TABLE IF NOT EXISTS raw.gridwatch_readings AS
        SELECT timestamp::TIMESTAMP AS timestamp, * EXCLUDE (timestamp) FROM df WHERE 1=0
    """)
    con.execute("""
        INSERT INTO raw.gridwatch_readings
        SELECT timestamp::TIMESTAMP AS timestamp, * EXCLUDE (timestamp) FROM df
        WHERE timestamp::TIMESTAMP NOT IN (SELECT timestamp FROM raw.gridwatch_readings)
    """)
    print(f"  gridwatch: {len(df):,} rows")


# ── IESO plant-level → fuel-type aggregation ──────────────────────────────

def migrate_ieso(con: duckdb.DuckDBPyConnection, data_dir: Path | None) -> None:
    mapping = get_plant_fuel_mapping()
    rows: list[dict] = []

    for year in IESO_YEARS:
        if data_dir:
            path = data_dir / "clean" / "ieso.ca" / "hourly" / "output" / f"{year}.csv"
            if not path.exists():
                continue
            df = pd.read_csv(path, index_col=0, low_memory=False)
        else:
            url = f"{RAW_BASE}/ieso.ca/hourly/output/{year}.csv"
            print(f"  Fetching IESO {year}")
            df = _fetch_csv(url)
            if df is None:
                continue

        df.index = pd.to_datetime(df.index, utc=True).strftime("%Y-%m-%dT%H:%M:%S")
        df.columns = df.columns.str.strip()
        gen_cols = [c for c in df.columns if c.upper() != "TOTAL"]

        for ts, row in df.iterrows():
            fuel_totals: dict[str, float] = {k: 0.0 for k in IESO_FUEL_COLS if k != "total"}
            for gen in gen_cols:
                val = row.get(gen)
                if pd.isna(val):
                    continue
                fuel = mapping.get(gen.strip().upper()) or infer_fuel_from_name(gen)
                fuel_totals[fuel if fuel in fuel_totals else "other"] += float(val)
            total_col = next((c for c in df.columns if c.upper() == "TOTAL"), None)
            total_val = row.get(total_col) if total_col else None
            total = float(total_val) if total_val is not None and pd.notna(total_val) else sum(fuel_totals.values())
            rows.append({"timestamp": ts, **fuel_totals, "total": total})

    if not rows:
        print("  IESO: no rows found")
        return

    result = pd.DataFrame(rows).drop_duplicates(subset=["timestamp"])
    con.execute("CREATE SCHEMA IF NOT EXISTS raw")
    con.execute("""
        CREATE TABLE IF NOT EXISTS raw.ieso_generation AS
        SELECT timestamp::TIMESTAMP AS timestamp, * EXCLUDE (timestamp) FROM result WHERE 1=0
    """)
    con.execute("""
        INSERT INTO raw.ieso_generation
        SELECT timestamp::TIMESTAMP AS timestamp, * EXCLUDE (timestamp) FROM result
        WHERE timestamp::TIMESTAMP NOT IN (SELECT timestamp FROM raw.ieso_generation)
    """)
    print(f"  IESO: {len(result):,} rows from {IESO_YEARS[0]}–{IESO_YEARS[-1]}")


# ── OEB rates ─────────────────────────────────────────────────────────────

def migrate_oeb(con: duckdb.DuckDBPyConnection, data_dir: Path | None) -> None:
    rows: list[dict] = []

    for filename in OEB_RATE_FILES:
        rate_type = filename.replace(".csv", "")
        if data_dir:
            path = data_dir / "clean" / "oeb.ca" / "electricity" / filename
            if not path.exists():
                print(f"  Skipping OEB {filename} — not found")
                continue
            df = pd.read_csv(path, index_col=0, parse_dates=True)
        else:
            url = f"{RAW_BASE}/oeb.ca/electricity/{quote(filename)}"
            print(f"  Fetching OEB {filename}")
            try:
                r = requests.get(url, timeout=30)
                r.raise_for_status()
                df = pd.read_csv(io.StringIO(r.text), index_col=0, parse_dates=True)
            except requests.HTTPError as e:
                print(f"  Warning: {e}", file=sys.stderr)
                continue

        df.index.name = "effective_date"
        for ts, row in df.iterrows():
            for col, val in row.items():
                rows.append({
                    "effective_date": pd.Timestamp(ts).date().isoformat(),
                    "rate_type": rate_type,
                    "rate_column": str(col),
                    "value_cents_per_kwh": float(val) if pd.notna(val) else None,
                })

    if not rows:
        print("  OEB: no rows found")
        return

    result = pd.DataFrame(rows).drop_duplicates(
        subset=["effective_date", "rate_type", "rate_column"]
    )
    con.execute("CREATE SCHEMA IF NOT EXISTS raw")
    con.execute("CREATE TABLE IF NOT EXISTS raw.oeb_rates AS SELECT * FROM result WHERE 1=0")
    con.execute("""
        INSERT INTO raw.oeb_rates
        SELECT * FROM result
        WHERE (effective_date, rate_type, rate_column)
          NOT IN (SELECT effective_date, rate_type, rate_column FROM raw.oeb_rates)
    """)
    print(f"  OEB: {len(result):,} rows")


# ── Entry point ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--data-dir", type=Path, default=None,
        help="Local ontario-grid-data checkout (default: fetch from GitHub)",
    )
    parser.add_argument("--db", default=DB_PATH)
    parser.add_argument(
        "--sources", nargs="*", choices=["gridwatch", "ieso", "oeb"],
        default=["gridwatch", "ieso", "oeb"],
    )
    args = parser.parse_args()

    src = f"local:{args.data_dir}" if args.data_dir else "github:ryanfobel/ontario-grid-data"
    print(f"Migrating historical data from {src} → {args.db}")
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
