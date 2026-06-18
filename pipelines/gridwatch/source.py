"""dlt source for gridwatch.ca — live Ontario grid data.

Ported from src/ontario_grid_data/gridwatch.py in ontario-grid-data.
Original uses Firefox; this version uses Chrome for CI compatibility.
Scrapes https://live.gridwatch.ca/home-page.html once per run and yields
the current hourly reading. dlt's merge + primary_key deduplicates.
"""
from __future__ import annotations

import datetime as dt
import re
from typing import Iterator

import dlt
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

GRIDWATCH_URL = "https://live.gridwatch.ca/home-page.html"

SOURCES = ["nuclear", "hydro", "gas", "wind", "biofuel", "solar"]

# Keys scraped via the "//p[contains(...)]" XPath pattern
_SUMMARY_TEXT_FIELDS = {
    "POWER GENERATED": ("power_generated_mw", "MW"),
    "ONTARIO DEMAND": ("ontario_demand_mw", "MW"),
    "TOTAL EMISSIONS": ("total_emissions_tonnes", "tonnes"),
    "CO2e INTENSITY": ("co2e_intensity_gco2_per_kwh", "g/kWh"),
}


@dlt.source(name="gridwatch")
def gridwatch_source() -> dlt.SourceReference:
    return gridwatch_readings()


@dlt.resource(
    name="gridwatch_readings",
    write_disposition="merge",
    primary_key="timestamp",
)
def gridwatch_readings() -> Iterator[dict]:
    driver = _make_driver()
    try:
        yield _scrape(driver)
    finally:
        driver.quit()


def _make_driver() -> webdriver.Chrome:
    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    return webdriver.Chrome(options=opts)


def _scrape(driver: webdriver.Chrome) -> dict:
    driver.get(GRIDWATCH_URL)

    time_of_reading = "updating data..."
    while time_of_reading == "updating data...":
        time_of_reading = driver.find_element(
            By.XPATH, '//span[@bind="timeOfReading"]/parent::div'
        ).text

    record: dict = {"timestamp": _parse_timestamp(time_of_reading)}

    # Imports / exports (span[@bind=...])
    for key in ["imports", "exports", "netImportExports"]:
        field = re.sub(r"(?<!^)(?=[A-Z])", "_", key).lower() + "_mw"
        val = driver.find_element(By.XPATH, f'//span[@bind="{key}"]/parent::div').text
        record[field] = _parse_float(val.replace(" MW", "").replace(",", ""))

    # Summary totals (p[contains(text(),...)])
    for label, (field, unit) in _SUMMARY_TEXT_FIELDS.items():
        val = driver.find_element(
            By.XPATH,
            f"//p[contains(text(), '{label}')]/parent::div/following-sibling::div",
        ).text
        cleaned = val.replace(f" {unit}", "").replace(",", "").strip()
        record[field] = _parse_float(cleaned)

    # Per-source output (MW) and percentage
    for source in SOURCES:
        pct_val = driver.find_element(
            By.XPATH, f'//span[@bind="{source}Percentage"]/parent::div'
        ).text
        out_val = driver.find_element(
            By.XPATH, f'//span[@bind="{source}Output"]/parent::div'
        ).text
        record[f"{source}_pct"] = _parse_float(pct_val.replace("%", ""))
        record[f"{source}_mw"] = _parse_float(out_val.replace(" MW", "").replace(",", ""))

    return record


def _parse_timestamp(time_of_reading: str) -> str:
    """Convert 'Thu Oct 14, 8 AM - 9 AM' → ISO 8601 datetime string (Eastern local)."""
    m = re.match(r"\w+ (\w+) (\d+), (\d+) (AM|PM)", time_of_reading)
    if not m:
        raise ValueError(f"Unexpected timeOfReading format: {time_of_reading!r}")
    month_str, day_str, hour_str, ampm = m.groups()
    hour = int(hour_str)
    if ampm == "PM" and hour != 12:
        hour += 12
    elif ampm == "AM" and hour == 12:
        hour = 0
    month = dt.datetime.strptime(month_str, "%b").month
    year = dt.datetime.now().year
    # Edge case: page shows December reading in January
    if dt.datetime.now().month == 1 and month == 12:
        year -= 1
    return dt.datetime(year, month, int(day_str), hour).isoformat()


def _parse_float(val: str) -> float | None:
    try:
        return float(val.strip())
    except (ValueError, AttributeError):
        return None
