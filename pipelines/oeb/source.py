"""dlt source for Ontario Energy Board electricity and natural gas rates.

Ported from src/ontario_grid_data/oeb.py in ontario-grid-data.
Fetches https://www.oeb.ca/.../historical-electricity-rates, parses the
rate tables by section heading, and yields rows in long format:
  (effective_date, rate_type, rate_column, value_cents_per_kwh)
"""
from __future__ import annotations

from typing import Iterator

import dlt
import pandas as pd
import requests
from bs4 import BeautifulSoup

OEB_ELECTRICITY_URL = (
    "https://www.oeb.ca/consumer-information-and-protection/"
    "electricity-rates/historical-electricity-rates"
)


@dlt.source(name="oeb")
def oeb_source() -> dlt.SourceReference:
    return oeb_rates()


@dlt.resource(
    name="oeb_rates",
    write_disposition="merge",
    primary_key=["effective_date", "rate_type", "rate_column"],
)
def oeb_rates() -> Iterator[dict]:
    r = requests.get(OEB_ELECTRICITY_URL, timeout=30)
    r.raise_for_status()
    soup = BeautifulSoup(r.content.decode("utf-8"), "lxml")

    # Each h2 with > 1 child is a rate-type heading; tables follow in the same order
    rate_types = [h2.contents[0] for h2 in soup.find_all("h2") if len(h2.contents) > 1]
    tables = soup.find_all("table")

    for rate_type, table in zip(rate_types, tables):
        try:
            df = _convert_electricity_table_to_df(table)
        except Exception as exc:
            print(f"Warning: could not parse table for {rate_type!r}: {exc}")
            continue

        rate_type_str = str(rate_type).strip()
        for ts, row in df.iterrows():
            for col, val in row.items():
                yield {
                    "effective_date": ts.date().isoformat(),
                    "rate_type": rate_type_str,
                    "rate_column": str(col),
                    "value_cents_per_kwh": float(val) if pd.notna(val) else None,
                }


# ---------------------------------------------------------------------------
# Parsing helpers — ported verbatim from oeb.py
# ---------------------------------------------------------------------------

def _make_subs(headers: list[str], subs: dict) -> list[str]:
    result = headers
    for a, b in subs.items():
        result = [s.replace(a, b).strip() for s in result]
    return result


def _convert_table_to_df(table) -> pd.DataFrame:
    rows = table.find_all("tr")
    headers = _make_subs(
        [th.text for th in rows[0].find_all("th")],
        subs={"\xa0": " ", "\n": "", "   ": " ", "*": ""},
    )
    rows = rows[1:]
    for i, tr in enumerate(rows):
        tds = [td.text for td in tr.find_all("td")]
        rows[i] = tds + (len(headers) - len(tds)) * [""]

    data: dict = {}
    for i, col in enumerate(headers):
        data[col] = _make_subs([row[i] for row in rows], subs={"*": "", ",": ""})
    return pd.DataFrame(data)


def _convert_electricity_table_to_df(table) -> pd.DataFrame:
    df = _convert_table_to_df(table)
    df = df.set_index("Effective date")
    df.index = pd.to_datetime(df.index)

    for col in df.columns:
        df[col] = df[col].str.replace(" ¢ per kWh", "", regex=False)

    threshold_col = "Residential threshold for lower tier price (kWh per month)"
    if threshold_col in df.columns:
        pat = r"(?P<summer>\S+) \(Summer\)\s+(?P<winter>\S+) \(Winter\)"
        special = df[threshold_col].str.extract(pat).dropna()
        df[threshold_col + " [Summer]"] = df[threshold_col]
        df[threshold_col + " [Winter]"] = df[threshold_col]
        df = df.drop(columns=[threshold_col])
        df.loc[special.index, threshold_col + " [Summer]"] = special["summer"]
        df.loc[special.index, threshold_col + " [Winter]"] = special["winter"]
        higher_col = "Higher tier price (¢ per kWh)"
        lower_col = "Lower tier price (¢ per kWh)"
        if higher_col in df.columns:
            na_index = df[df[higher_col] == ""].index
            df.loc[na_index, threshold_col + " [Summer]"] = 0
            df.loc[na_index, threshold_col + " [Winter]"] = 0
            df.loc[na_index, higher_col] = df.loc[na_index, lower_col]

    for col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    return df
