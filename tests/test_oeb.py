"""Tests for OEB source parsing logic."""
from unittest.mock import MagicMock, patch

import pytest

from pipelines.oeb.source import _convert_electricity_table_to_df, _convert_table_to_df

# Minimal HTML matching the real OEB page structure
SAMPLE_OEB_HTML = """
<html><body>
<h2><span>Time-of-Use Prices</span></h2>
<table>
  <tr>
    <th>Effective date</th>
    <th>Off-Peak Price (¢ per kWh)</th>
    <th>Mid-Peak Price (¢ per kWh)</th>
    <th>On-Peak Price (¢ per kWh)</th>
  </tr>
  <tr>
    <td>May 1, 2024</td>
    <td>8.7 ¢ per kWh</td>
    <td>12.2 ¢ per kWh</td>
    <td>18.2 ¢ per kWh</td>
  </tr>
  <tr>
    <td>November 1, 2023</td>
    <td>8.2 ¢ per kWh</td>
    <td>11.3 ¢ per kWh</td>
    <td>17.0 ¢ per kWh</td>
  </tr>
</table>
</body></html>
"""


class TestOebParsing:
    def _get_table(self):
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(SAMPLE_OEB_HTML, "lxml")
        return soup.find("table")

    def test_convert_table_returns_dataframe(self):
        table = self._get_table()
        df = _convert_table_to_df(table)
        assert len(df) == 2
        assert "Effective date" in df.columns

    def test_electricity_table_has_datetime_index(self):
        table = self._get_table()
        df = _convert_electricity_table_to_df(table)
        import pandas as pd
        assert isinstance(df.index, pd.DatetimeIndex)

    def test_electricity_table_numeric_values(self):
        table = self._get_table()
        df = _convert_electricity_table_to_df(table)
        assert df.loc[:, "Off-Peak Price (¢ per kWh)"].dtype == float
        assert df["Off-Peak Price (¢ per kWh)"].iloc[0] == pytest.approx(8.7)
        assert df["On-Peak Price (¢ per kWh)"].iloc[0] == pytest.approx(18.2)

    def test_electricity_table_row_count(self):
        table = self._get_table()
        df = _convert_electricity_table_to_df(table)
        assert len(df) == 2

    def test_oeb_blocked_yields_nothing(self):
        import requests
        from pipelines.oeb.source import oeb_rates
        with patch("pipelines.oeb.source.requests.get") as mock_get:
            resp = MagicMock(status_code=403)
            resp.raise_for_status.side_effect = requests.HTTPError("403 Forbidden")
            mock_get.return_value = resp
            rows = list(oeb_rates())
        assert rows == []
