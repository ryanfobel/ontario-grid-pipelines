"""Tests for gridwatch source parsing logic."""
import pytest

from pipelines.gridwatch.source import _parse_float, _parse_timestamp


class TestTimestampParsing:
    @pytest.mark.parametrize("raw,expected", [
        ("Thu Oct 14, 8 AM - 9 AM",  "2026-10-14T08:00:00"),
        ("Mon Jan  5, 12 PM - 1 PM", "2026-01-05T12:00:00"),
        ("Wed Jun  1, 12 AM - 1 AM", "2026-06-01T00:00:00"),
        ("Fri Dec 31, 11 PM - 12 AM","2026-12-31T23:00:00"),
    ])
    def test_parse(self, raw, expected):
        import datetime
        # Pass a fixed "today" directly to avoid monkeypatching datetime
        result = _parse_timestamp(raw, today=datetime.date(2026, 6, 19))
        assert result == expected

    def test_invalid_raises(self):
        with pytest.raises(ValueError, match="Unexpected"):
            _parse_timestamp("not a valid string")


class TestParseFloat:
    def test_numeric_string(self):
        assert _parse_float("1234.5") == pytest.approx(1234.5)

    def test_strips_whitespace(self):
        assert _parse_float("  42.0  ") == pytest.approx(42.0)

    def test_empty_string_returns_none(self):
        assert _parse_float("") is None

    def test_non_numeric_returns_none(self):
        assert _parse_float("N/A") is None
