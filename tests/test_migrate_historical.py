"""Tests for migrate_historical timestamp normalization."""
import pandas as pd


def _normalize_gridwatch_index(idx):
    """Mirrors the logic in migrate_gridwatch."""
    return pd.to_datetime(idx, utc=True).tz_localize(None).strftime("%Y-%m-%dT%H:%M:%S")


class TestGridwatchTimestampNormalization:
    def test_mixed_timezones_resolved(self):
        idx = pd.Index([
            "2023-03-12 01:00:00-05:00",  # EST
            "2023-03-12 03:00:00-04:00",  # EDT
        ])
        result = _normalize_gridwatch_index(idx)
        assert list(result) == ["2023-03-12T06:00:00", "2023-03-12T07:00:00"]

    def test_naive_timestamps_treated_as_utc(self):
        idx = pd.Index(["2024-01-01 00:00:00", "2024-06-01 12:00:00"])
        result = _normalize_gridwatch_index(idx)
        assert list(result) == ["2024-01-01T00:00:00", "2024-06-01T12:00:00"]

    def test_output_is_naive_iso8601(self):
        idx = pd.Index(["2024-07-04 15:30:00-04:00"])
        result = _normalize_gridwatch_index(idx)
        assert result[0] == "2024-07-04T19:30:00"
        assert "+" not in result[0] and "Z" not in result[0]
