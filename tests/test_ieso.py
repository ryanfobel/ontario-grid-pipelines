"""Tests for IESO source parsing logic."""
import io
from datetime import date
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from pipelines.ieso.source import (
    _infer_fuel_from_name,
    _next_month,
    _yield_from_csv,
    _yield_from_excel,
)

# Minimal fuel-mix CSV matching the real IESO format
SAMPLE_FUEL_MIX_CSV = """\
Date,Hour,Nuclear,Gas,Hydro,Wind,Solar,Biofuel,Total
2024-06-01,1,10000,2000,3000,1500,0,50,16550
2024-06-01,2,10000,1800,2900,1600,0,50,16350
2024-06-01,3,10000,1700,2800,1700,0,50,16250
"""


class TestFuelMixCsvParsing:
    def test_yields_correct_number_of_rows(self):
        with patch("pipelines.ieso.source.requests.get") as mock_get:
            mock_get.return_value = MagicMock(
                ok=True, text=SAMPLE_FUEL_MIX_CSV, status_code=200
            )
            mock_get.return_value.raise_for_status = lambda: None
            rows = list(_yield_from_csv(2024, 6))
        assert len(rows) == 3

    def test_timestamp_format(self):
        with patch("pipelines.ieso.source.requests.get") as mock_get:
            mock_get.return_value = MagicMock(
                ok=True, text=SAMPLE_FUEL_MIX_CSV, status_code=200
            )
            mock_get.return_value.raise_for_status = lambda: None
            rows = list(_yield_from_csv(2024, 6))
        assert rows[0]["timestamp"] == "2024-06-01T00:00:00"
        assert rows[1]["timestamp"] == "2024-06-01T01:00:00"

    def test_fuel_columns_present(self):
        with patch("pipelines.ieso.source.requests.get") as mock_get:
            mock_get.return_value = MagicMock(
                ok=True, text=SAMPLE_FUEL_MIX_CSV, status_code=200
            )
            mock_get.return_value.raise_for_status = lambda: None
            rows = list(_yield_from_csv(2024, 6))
        row = rows[0]
        assert row["nuclear"] == pytest.approx(10000)
        assert row["gas"] == pytest.approx(2000)
        assert row["total"] == pytest.approx(16550)

    def test_http_error_yields_nothing(self):
        import requests
        with patch("pipelines.ieso.source.requests.get") as mock_get:
            resp = MagicMock(status_code=403)
            resp.raise_for_status.side_effect = requests.HTTPError("403")
            mock_get.return_value = resp
            rows = list(_yield_from_csv(2024, 6))
        assert rows == []


class TestFuelInference:
    @pytest.mark.parametrize("name,expected", [
        ("Bruce B4", "nuclear"),
        ("Pickering A1", "nuclear"),
        ("Darlington GS", "nuclear"),
        ("Beck GS Niagara Falls", "hydro"),
        ("Saunders GS", "hydro"),
        ("Ontario Wind Farm", "wind"),
        ("Atikokan Solar", "solar"),
        ("Port Lands Cogen", "gas"),
        ("Lennox GS", "gas"),
        ("Biomass plant", "biofuel"),
        ("Mystery plant 42", "other"),
    ])
    def test_inference(self, name, expected):
        assert _infer_fuel_from_name(name) == expected


class TestExcelParsing:
    def _make_excel_bytes(self) -> bytes:
        """Create a minimal GOC-style Excel file."""
        df = pd.DataFrame({
            "DATE": pd.to_datetime(["2015-01-01", "2015-01-01"]),
            "HOUR": [1, 2],
            "Bruce B4": [800.0, 810.0],
            "Beck GS Niagara": [400.0, 390.0],
            "Ontario Wind Farm": [50.0, 60.0],
            "TOTAL": [1250.0, 1260.0],
        })
        buf = io.BytesIO()
        df.to_excel(buf, index=False, engine="openpyxl")
        buf.seek(0)
        return buf.read()

    def test_yields_correct_rows(self):
        excel_bytes = self._make_excel_bytes()
        with patch("pipelines.ieso.source.requests.get") as mock_get:
            mock_get.return_value = MagicMock(
                ok=True, content=excel_bytes, status_code=200
            )
            mock_get.return_value.raise_for_status = lambda: None
            rows = list(_yield_from_excel(
                "http://fake/GOC-2015.ashx", {},
                date(2015, 1, 1), date(2015, 12, 31), year=2015,
            ))
        assert len(rows) == 2

    def test_fuel_aggregation_with_mapping(self):
        excel_bytes = self._make_excel_bytes()
        mapping = {
            "BRUCE B4": "nuclear",
            "BECK GS NIAGARA": "hydro",
            "ONTARIO WIND FARM": "wind",
        }
        with patch("pipelines.ieso.source.requests.get") as mock_get:
            mock_get.return_value = MagicMock(
                ok=True, content=excel_bytes, status_code=200
            )
            mock_get.return_value.raise_for_status = lambda: None
            rows = list(_yield_from_excel(
                "http://fake/GOC-2015.ashx", mapping,
                date(2015, 1, 1), date(2015, 12, 31), year=2015,
            ))
        assert rows[0]["nuclear"] == pytest.approx(800.0)
        assert rows[0]["hydro"] == pytest.approx(400.0)
        assert rows[0]["wind"] == pytest.approx(50.0)
        assert rows[0]["total"] == pytest.approx(1250.0)  # from Excel TOTAL column

    def test_timestamp_is_hour_starting(self):
        excel_bytes = self._make_excel_bytes()
        with patch("pipelines.ieso.source.requests.get") as mock_get:
            mock_get.return_value = MagicMock(
                ok=True, content=excel_bytes, status_code=200
            )
            mock_get.return_value.raise_for_status = lambda: None
            rows = list(_yield_from_excel(
                "http://fake/GOC-2015.ashx", {},
                date(2015, 1, 1), date(2015, 12, 31),
            ))
        # HOUR=1 → 0-based → T00:00:00; HOUR=2 → T01:00:00
        assert rows[0]["timestamp"] == "2015-01-01T00:00:00"
        assert rows[1]["timestamp"] == "2015-01-01T01:00:00"

    def test_date_filter(self):
        excel_bytes = self._make_excel_bytes()
        with patch("pipelines.ieso.source.requests.get") as mock_get:
            mock_get.return_value = MagicMock(
                ok=True, content=excel_bytes, status_code=200
            )
            mock_get.return_value.raise_for_status = lambda: None
            # Only ask for rows before 2015-01-01 → none
            rows = list(_yield_from_excel(
                "http://fake/GOC-2015.ashx", {},
                date(2014, 1, 1), date(2014, 12, 31),
            ))
        assert rows == []


class TestNextMonth:
    def test_mid_year(self):
        assert _next_month(date(2024, 6, 1)) == date(2024, 7, 1)

    def test_december_rolls_over(self):
        assert _next_month(date(2024, 12, 1)) == date(2025, 1, 1)
