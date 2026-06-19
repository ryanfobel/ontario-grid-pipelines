"""dlt source for IESO hourly generation data by fuel type.

Three data paths, unified into a single incremental resource:

  2010–2018      GOC annual Excel files (.ashx) — plant-level output,
                 aggregated to fuel types using plant→fuel mapping from
                 the IESO daily XML report (available ~3 months back).

  2019-01–04     GOC-2019-Jan-April.ashx — same Excel format.

  2019-05+       Monthly fuel-mix CSVs (.../fuel-mix/YYYYMM.csv) —
                 already aggregated by fuel type, no plant mapping needed.

On first run (or --full-refresh) the entire history from 2010 is loaded.
On incremental runs only new months are fetched.
"""
from __future__ import annotations

import io
import xml.etree.ElementTree as ET
from datetime import date, timedelta
from typing import Iterator

import dlt
import pandas as pd
import requests

FUEL_MIX_URL = (
    "https://www.ieso.ca/-/media/Files/IESO/Power-Data/fuel-mix/{year}{month:02d}.csv"
)
GOC_EXCEL_URL = (
    "https://ieso.ca/-/media/Files/IESO/Power-Data/data-directory/GOC-{year}.ashx"
)
GOC_2019_JAN_APR_URL = (
    "https://ieso.ca/-/media/Files/IESO/Power-Data/data-directory/GOC-2019-Jan-April.ashx"
)
XML_DAILY_URL = (
    "http://reports.ieso.ca/public/GenOutputCapability/PUB_GenOutputCapability_{date}.xml"
)
XML_NS = "{http://www.theIMO.com/schema}"

FUEL_COLS = ["nuclear", "gas", "hydro", "wind", "solar", "biofuel", "other", "total"]
# Columns present in the 2019-05+ fuel-mix CSV (no "other" category)
CSV_FUEL_COLS = ["nuclear", "gas", "hydro", "wind", "solar", "biofuel", "total"]


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
        initial_value="2010-01-01T00:00:00",
    ),
) -> Iterator[dict]:
    start = date.fromisoformat(updated_at.start_value[:10])
    end = date.today()

    # ── Pre-2019: GOC Excel files ──────────────────────────────────────────
    if start < date(2019, 5, 1):
        mapping = _get_plant_fuel_mapping()

        for year in range(max(2010, start.year), 2019):
            print(f"IESO: fetching GOC Excel {year}")
            yield from _yield_from_excel(
                GOC_EXCEL_URL.format(year=year), mapping, start, end, year=year
            )

        # Jan–Apr 2019 special file
        if end >= date(2019, 1, 1):
            print("IESO: fetching GOC-2019-Jan-April Excel")
            yield from _yield_from_excel(
                GOC_2019_JAN_APR_URL, mapping,
                max(start, date(2019, 1, 1)), min(end, date(2019, 4, 30)),
            )

    # ── 2019-05+: fuel-mix CSV ─────────────────────────────────────────────
    csv_start = date(max(start.year, 2019), 5 if start < date(2019, 5, 1) else start.month, 1)
    if start >= date(2019, 5, 1):
        csv_start = date(start.year, start.month, 1)
    else:
        csv_start = date(2019, 5, 1)

    cursor = csv_start
    while cursor <= end:
        yield from _yield_from_csv(cursor.year, cursor.month)
        cursor = _next_month(cursor)


# ── Plant→fuel mapping ────────────────────────────────────────────────────

def _get_plant_fuel_mapping() -> dict[str, str]:
    """Fetch generator→fuel-type mapping from the most recent available IESO daily XML."""
    for days_back in range(1, 10):
        target = (date.today() - timedelta(days=days_back)).strftime("%Y%m%d")
        url = XML_DAILY_URL.format(date=target)
        try:
            r = requests.get(url, timeout=30)
            if r.ok:
                m = _parse_xml_mapping(r.text)
                print(f"IESO: loaded plant→fuel mapping for {len(m)} generators from {target}")
                return m
        except requests.RequestException:
            continue
    print("IESO: could not fetch XML mapping; falling back to name inference")
    return {}


def _parse_xml_mapping(xml_text: str) -> dict[str, str]:
    root = ET.fromstring(xml_text)
    generators = (
        root.find(f"{XML_NS}IMODocBody")
        .find(f"{XML_NS}Generators")
        .findall(f"{XML_NS}Generator")
    )
    return {
        _norm(gen.find(f"{XML_NS}GeneratorName").text): gen.find(f"{XML_NS}FuelType").text.lower()
        for gen in generators
    }


def _infer_fuel_from_name(name: str) -> str:
    """Best-effort fuel classification by generator name for generators not in XML."""
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


def _norm(name: str) -> str:
    return name.strip().upper()


# ── Excel path (2010–2019-04) ─────────────────────────────────────────────

def _yield_from_excel(
    url: str,
    mapping: dict[str, str],
    start: date,
    end: date,
    year: int | None = None,
) -> Iterator[dict]:
    try:
        r = requests.get(url, timeout=180)
        r.raise_for_status()
    except requests.RequestException as exc:
        print(f"IESO: skipping {url}: {exc}")
        return

    df = pd.read_excel(io.BytesIO(r.content), engine="openpyxl")

    # Year-specific quirks documented in the original core.py
    if year is not None:
        drop_cols = {2010: "Unnamed: 2", 2011: "Unnamed: 2", 2012: "a"}
        if year in drop_cols:
            df = df.drop(columns=[drop_cols[year]], errors="ignore")

    df = df.rename(columns={"Hour": "HOUR", "Date": "DATE"})
    df = df[pd.notna(df["DATE"])].copy()
    df["HOUR"] = df["HOUR"].astype(int) - 1  # 1-based → 0-based

    gen_cols = [c for c in df.columns if c not in {"DATE", "HOUR", "TOTAL"}]

    for _, row in df.iterrows():
        try:
            row_date = row["DATE"].date()
        except AttributeError:
            row_date = pd.Timestamp(row["DATE"]).date()

        if row_date < start or row_date > end:
            continue

        timestamp = f"{row_date.isoformat()}T{int(row['HOUR']):02}:00:00"
        fuel_totals: dict[str, float] = {f: 0.0 for f in FUEL_COLS if f != "total"}

        for gen in gen_cols:
            val = row.get(gen)
            if pd.isna(val):
                continue
            fuel = mapping.get(_norm(str(gen))) or _infer_fuel_from_name(str(gen))
            fuel_totals[fuel if fuel in fuel_totals else "other"] += float(val)

        # Prefer the Excel's own TOTAL if present (catches any generators we missed)
        excel_total = row.get("TOTAL")
        total = float(excel_total) if pd.notna(excel_total) else sum(fuel_totals.values())

        yield {"timestamp": timestamp, **fuel_totals, "total": total}


# ── CSV path (2019-05+) ───────────────────────────────────────────────────

def _yield_from_csv(year: int, month: int) -> Iterator[dict]:
    url = FUEL_MIX_URL.format(year=year, month=month)
    try:
        r = requests.get(url, timeout=30)
        r.raise_for_status()
    except requests.HTTPError:
        return

    df = pd.read_csv(io.StringIO(r.text))
    df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_", regex=False)
    df["timestamp"] = (
        pd.to_datetime(df["date"]) + pd.to_timedelta(df["hour"].astype(int) - 1, unit="h")
    ).dt.strftime("%Y-%m-%dT%H:00:00")

    for row in df.itertuples(index=False):
        yield {
            "timestamp": row.timestamp,
            **{col: getattr(row, col, None) for col in CSV_FUEL_COLS if hasattr(row, col)},
            "other": None,
        }


def _next_month(d: date) -> date:
    return date(d.year + 1, 1, 1) if d.month == 12 else date(d.year, d.month + 1, 1)
