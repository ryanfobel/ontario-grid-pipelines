"""dlt source for gridwatch.ca hourly readings (CO2 intensity + generation mix).

Ported from src/ontario_grid_data/gridwatch.py in ontario-grid-data.
The original uses Selenium because the site renders data via JavaScript.
"""
from __future__ import annotations

from typing import Iterator

import dlt
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


GRIDWATCH_URL = "https://gridwatch.ca/"


@dlt.source(name="gridwatch")
def gridwatch_source() -> dlt.SourceReference:
    return gridwatch_readings()


@dlt.resource(
    name="gridwatch_readings",
    write_disposition="merge",
    primary_key="timestamp",
)
def gridwatch_readings(
    updated_at: dlt.sources.incremental[str] = dlt.sources.incremental(
        "timestamp",
        initial_value=None,
    ),
) -> Iterator[dict]:
    driver = _make_driver()
    try:
        yield from _scrape(driver)
    finally:
        driver.quit()


def _make_driver() -> webdriver.Chrome:
    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    return webdriver.Chrome(options=opts)


def _scrape(driver: webdriver.Chrome) -> Iterator[dict]:
    """Scrape current grid data from gridwatch.ca.

    TODO: port the full historical-fetch logic from the original gridwatch.py.
    The original code downloads hourly data for a date range. This stub only
    captures the current reading as a starting point.
    """
    driver.get(GRIDWATCH_URL)
    WebDriverWait(driver, 15).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "[data-timestamp]"))
    )

    # TODO: extract timestamp and readings from the page DOM.
    # Yield dicts with at minimum:
    #   timestamp (ISO 8601), co2_intensity_gco2_per_kwh, generation_mw
    raise NotImplementedError(
        "Port scraping logic from ontario-grid-data/src/ontario_grid_data/gridwatch.py"
    )
