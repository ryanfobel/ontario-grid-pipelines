"""dlt source for Ontario Energy Board electricity rates.

Ported from src/ontario_grid_data/oeb.py in ontario-grid-data.
Scrapes time-of-use and tiered rates from the OEB website.
"""
from __future__ import annotations

from typing import Iterator

import dlt
import requests
from bs4 import BeautifulSoup

OEB_RATES_URL = "https://www.oeb.ca/consumer-information-and-protection/electricity-rates"


@dlt.source(name="oeb")
def oeb_source() -> dlt.SourceReference:
    return oeb_rates()


@dlt.resource(
    name="oeb_rates",
    write_disposition="merge",
    primary_key=["effective_date", "rate_class"],
)
def oeb_rates() -> Iterator[dict]:
    """Fetch current and historical OEB electricity rates.

    TODO: port the full scraping logic from ontario-grid-data/src/ontario_grid_data/oeb.py.
    Yield dicts with at minimum:
      effective_date (ISO date), rate_class (str), rate_cents_per_kwh (float)
    """
    r = requests.get(OEB_RATES_URL, timeout=30)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "lxml")

    # TODO: parse rate tables from soup.
    # The original oeb.py scrapes both Time-of-Use and tiered rate tables.
    raise NotImplementedError(
        "Port scraping logic from ontario-grid-data/src/ontario_grid_data/oeb.py"
    )
