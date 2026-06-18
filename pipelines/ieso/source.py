"""dlt source for IESO hourly generation data by fuel type.

Data source: https://www.ieso.ca/power-data/supply-overview/transmission-connected-generation
- 2019–present: monthly CSV at .../fuel-mix/YYYYMM.csv
- Pre-2019: Excel files (migrate_historical.py handles the backfill)
"""
from __future__ import annotations

import io
from datetime import date
from typing import Iterator

import dlt
import pandas as pd
import requests

FUEL_MIX_URL = (
    "https://www.ieso.ca/-/media/Files/IESO/Power-Data/fuel-mix/{year}{month:02d}.csv"
)
FUEL_COLS = ["nuclear", "gas", "hydro", "wind", "solar", "biofuel", "total"]


@dlt.source(name="ieso")
def ieso_source() -> dlt.SourceReference:
    return ieso_generation()


@dlt.resource(
    name="ieso_generation",
    write_disposition="merge",
    primary_key="timestamp",
)
def ieso_generation(
    updated_at: dlt.sources.incremental[str] = dlt.sources.incremental(
        "timestamp",
        initial_value="2019-01-01T00:00:00",
    ),
) -> Iterator[dict]:
    start = date.fromisoformat(updated_at.start_value[:10])
    end = date.today()

    cursor = date(start.year, start.month, 1)
    while cursor <= end:
        yield from _fetch_month(cursor.year, cursor.month)
        cursor = _next_month(cursor)


def _fetch_month(year: int, month: int) -> Iterator[dict]:
    url = FUEL_MIX_URL.format(year=year, month=month)
    try:
        r = requests.get(url, timeout=30)
        r.raise_for_status()
    except requests.HTTPError:
        return

    df = pd.read_csv(io.StringIO(r.text))
    df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_", regex=False)

    # Build ISO timestamp: Date column + Hour (1-based) → hour-ending convention
    df["timestamp"] = (
        pd.to_datetime(df["date"]) + pd.to_timedelta(df["hour"].astype(int) - 1, unit="h")
    ).dt.strftime("%Y-%m-%dT%H:00:00")

    for row in df.itertuples(index=False):
        yield {
            "timestamp": row.timestamp,
            **{col: getattr(row, col, None) for col in FUEL_COLS if hasattr(row, col)},
        }


def _next_month(d: date) -> date:
    return date(d.year + 1, 1, 1) if d.month == 12 else date(d.year, d.month + 1, 1)
