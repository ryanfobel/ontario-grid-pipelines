"""Tests for freshness check logic in pipeline.py."""
import os
import tempfile
from datetime import datetime, timedelta, timezone

import duckdb
import pytest

import pipeline
from pipeline import FRESHNESS_THRESHOLD


class TestFreshnessChecks:
    """Test freshness logic for all three sources."""

    @pytest.fixture
    def temp_db(self):
        """Create a temporary DuckDB database for testing."""
        # Get a temp file path but don't create the file - let DuckDB initialize it
        fd, db_path = tempfile.mkstemp(suffix=".duckdb")
        os.close(fd)  # Close the file descriptor
        os.unlink(db_path)  # Remove the empty file
        yield db_path
        if os.path.exists(db_path):
            os.unlink(db_path)

    def _setup_gridwatch_data(self, db_path: str, timestamp: datetime):
        """Populate gridwatch_readings table with test data."""
        con = duckdb.connect(db_path)
        con.execute("CREATE SCHEMA IF NOT EXISTS raw")
        con.execute("""
            CREATE TABLE IF NOT EXISTS raw.gridwatch_readings (
                timestamp TIMESTAMP PRIMARY KEY,
                nuclear DOUBLE,
                total DOUBLE
            )
        """)
        con.execute(
            "INSERT INTO raw.gridwatch_readings VALUES (?, 10000.0, 15000.0)",
            [timestamp]
        )
        con.close()

    def _setup_ieso_data(self, db_path: str, timestamp: datetime):
        """Populate ieso_generation table with test data."""
        con = duckdb.connect(db_path)
        con.execute("CREATE SCHEMA IF NOT EXISTS raw")
        con.execute("""
            CREATE TABLE IF NOT EXISTS raw.ieso_generation (
                timestamp TIMESTAMP PRIMARY KEY,
                nuclear DOUBLE,
                total DOUBLE
            )
        """)
        con.execute(
            "INSERT INTO raw.ieso_generation VALUES (?, 10000.0, 15000.0)",
            [timestamp]
        )
        con.close()

    def _setup_oeb_data(self, db_path: str, effective_date: datetime):
        """Populate oeb_rates table with test data."""
        con = duckdb.connect(db_path)
        con.execute("CREATE SCHEMA IF NOT EXISTS raw")
        con.execute("""
            CREATE TABLE IF NOT EXISTS raw.oeb_rates (
                effective_date DATE,
                rate_type VARCHAR,
                rate_column VARCHAR,
                value_cents_per_kwh DOUBLE,
                PRIMARY KEY (effective_date, rate_type, rate_column)
            )
        """)
        con.execute(
            "INSERT INTO raw.oeb_rates VALUES (?, 'test', 'test', 10.5)",
            [effective_date.date()]
        )
        con.close()

    # ── Gridwatch tests (1 hour threshold) ───────────────────────────────────

    def test_gridwatch_fresh_30_minutes_ago(self, temp_db, monkeypatch):
        """Gridwatch data from 30 minutes ago should be considered fresh."""
        monkeypatch.setattr(pipeline, "DB_PATH", temp_db)

        now = datetime.now(timezone.utc)
        thirty_min_ago = now - timedelta(minutes=30)
        # Store as naive datetime (DuckDB will treat it as-is, not convert timezones)
        self._setup_gridwatch_data(temp_db, thirty_min_ago.replace(tzinfo=None))

        assert pipeline.is_fresh("gridwatch") is True

    def test_gridwatch_stale_2_hours_ago(self, temp_db, monkeypatch):
        """Gridwatch data from 2 hours ago should be considered stale."""
        monkeypatch.setattr(pipeline, "DB_PATH", temp_db)

        now = datetime.now(timezone.utc)
        two_hours_ago = now - timedelta(hours=2)
        self._setup_gridwatch_data(temp_db, two_hours_ago)

        assert pipeline.is_fresh("gridwatch") is False

    def test_gridwatch_exact_threshold(self, temp_db, monkeypatch):
        """Gridwatch data at exactly the threshold should be stale."""
        monkeypatch.setattr(pipeline, "DB_PATH", temp_db)

        now = datetime.now(timezone.utc)
        one_hour_ago = now - FRESHNESS_THRESHOLD["gridwatch"]
        self._setup_gridwatch_data(temp_db, one_hour_ago)

        # At exactly the threshold, data is no longer fresh
        assert pipeline.is_fresh("gridwatch") is False

    # ── IESO tests (1 day threshold) ─────────────────────────────────────────

    def test_ieso_fresh_12_hours_ago(self, temp_db, monkeypatch):
        """IESO data from 12 hours ago should be considered fresh."""
        monkeypatch.setattr(pipeline, "DB_PATH", temp_db)

        now = datetime.now(timezone.utc)
        twelve_hours_ago = now - timedelta(hours=12)
        self._setup_ieso_data(temp_db, twelve_hours_ago)

        assert pipeline.is_fresh("ieso") is True

    def test_ieso_stale_2_days_ago(self, temp_db, monkeypatch):
        """IESO data from 2 days ago should be considered stale."""
        monkeypatch.setattr(pipeline, "DB_PATH", temp_db)

        now = datetime.now(timezone.utc)
        two_days_ago = now - timedelta(days=2)
        self._setup_ieso_data(temp_db, two_days_ago)

        assert pipeline.is_fresh("ieso") is False

    def test_ieso_exact_threshold(self, temp_db, monkeypatch):
        """IESO data at exactly the threshold should be stale."""
        monkeypatch.setattr(pipeline, "DB_PATH", temp_db)

        now = datetime.now(timezone.utc)
        one_day_ago = now - FRESHNESS_THRESHOLD["ieso"]
        self._setup_ieso_data(temp_db, one_day_ago)

        assert pipeline.is_fresh("ieso") is False

    # ── OEB tests (7 day threshold) ──────────────────────────────────────────

    def test_oeb_fresh_3_days_ago(self, temp_db, monkeypatch):
        """OEB data from 3 days ago should be considered fresh."""
        monkeypatch.setattr(pipeline, "DB_PATH", temp_db)

        now = datetime.now(timezone.utc)
        three_days_ago = now - timedelta(days=3)
        self._setup_oeb_data(temp_db, three_days_ago)

        assert pipeline.is_fresh("oeb") is True

    def test_oeb_stale_10_days_ago(self, temp_db, monkeypatch):
        """OEB data from 10 days ago should be considered stale."""
        monkeypatch.setattr(pipeline, "DB_PATH", temp_db)

        now = datetime.now(timezone.utc)
        ten_days_ago = now - timedelta(days=10)
        self._setup_oeb_data(temp_db, ten_days_ago)

        assert pipeline.is_fresh("oeb") is False

    def test_oeb_exact_threshold(self, temp_db, monkeypatch):
        """OEB data at exactly the threshold should be stale."""
        monkeypatch.setattr(pipeline, "DB_PATH", temp_db)

        now = datetime.now(timezone.utc)
        seven_days_ago = now - FRESHNESS_THRESHOLD["oeb"]
        self._setup_oeb_data(temp_db, seven_days_ago)

        assert pipeline.is_fresh("oeb") is False

    # ── Edge cases ────────────────────────────────────────────────────────────

    def test_unknown_source_not_fresh(self, temp_db, monkeypatch):
        """Unknown sources should never be considered fresh."""
        monkeypatch.setattr(pipeline, "DB_PATH", temp_db)

        assert pipeline.is_fresh("unknown_source") is False

    def test_empty_table_not_fresh(self, temp_db, monkeypatch):
        """Empty tables should not be considered fresh."""
        monkeypatch.setattr(pipeline, "DB_PATH", temp_db)

        # Create empty gridwatch table
        con = duckdb.connect(temp_db)
        con.execute("CREATE SCHEMA IF NOT EXISTS raw")
        con.execute("""
            CREATE TABLE IF NOT EXISTS raw.gridwatch_readings (
                timestamp TIMESTAMP PRIMARY KEY,
                nuclear DOUBLE
            )
        """)
        con.close()

        assert pipeline.is_fresh("gridwatch") is False

    def test_missing_table_not_fresh(self, temp_db, monkeypatch):
        """Missing tables should not be considered fresh."""
        monkeypatch.setattr(pipeline, "DB_PATH", temp_db)

        # Create schema but no tables
        con = duckdb.connect(temp_db)
        con.execute("CREATE SCHEMA IF NOT EXISTS raw")
        con.close()

        assert pipeline.is_fresh("gridwatch") is False

    def test_null_timestamp_not_fresh(self, temp_db, monkeypatch):
        """Tables with NULL timestamps should not be considered fresh."""
        monkeypatch.setattr(pipeline, "DB_PATH", temp_db)

        con = duckdb.connect(temp_db)
        con.execute("CREATE SCHEMA IF NOT EXISTS raw")
        con.execute("""
            CREATE TABLE IF NOT EXISTS raw.gridwatch_readings (
                timestamp TIMESTAMP,
                nuclear DOUBLE
            )
        """)
        con.execute("INSERT INTO raw.gridwatch_readings VALUES (NULL, 10000.0)")
        con.close()

        assert pipeline.is_fresh("gridwatch") is False

    def test_timezone_naive_timestamp_handled(self, temp_db, monkeypatch):
        """Timezone-naive timestamps should be treated as UTC."""
        monkeypatch.setattr(pipeline, "DB_PATH", temp_db)

        now = datetime.now(timezone.utc)
        thirty_min_ago = now - timedelta(minutes=30)
        # Store without timezone info
        naive_timestamp = thirty_min_ago.replace(tzinfo=None)
        self._setup_gridwatch_data(temp_db, naive_timestamp)

        # Should still work because is_fresh adds UTC timezone
        assert pipeline.is_fresh("gridwatch") is True
