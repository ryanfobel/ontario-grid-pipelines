# Pipeline Reliability & Resilience Design

## Overview

This document outlines reliability improvements for the ontario-grid-pipelines data pipeline to handle failures, missed runs, and data quality issues gracefully.

## Current State

### What Works ✅
- **Graceful degradation**: Sources catch HTTP errors and continue
- **Idempotent operations**: dlt `merge` disposition allows safe re-runs
- **Workflow resilience**: GitHub Actions continues if one source fails
- **Database fallback**: Fresh start if restore from data branch fails
- **Basic freshness**: Gridwatch skip logic prevents redundant scrapes

### Gaps ❌
- No retry logic for transient failures (network, rate limits)
- No catch-up when scheduler misses runs
- No alerting on persistent failures
- No quality validation before committing data
- Limited freshness checks (only gridwatch)

## Proposed Enhancements

### 1. Retry Logic with Exponential Backoff

**Problem**: Transient network failures, timeouts, and rate limits cause unnecessary pipeline failures.

**Solution**: Add retry decorator using `tenacity` library.

```python
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log
)
import logging

logger = logging.getLogger(__name__)

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=2, min=2, max=30),
    retry=retry_if_exception_type((requests.Timeout, requests.ConnectionError)),
    before_sleep=before_sleep_log(logger, logging.WARNING)
)
def fetch_with_retry(url: str, **kwargs) -> requests.Response:
    """Fetch URL with exponential backoff retry."""
    return requests.get(url, **kwargs)
```

**Configuration**:
- 3 attempts maximum
- Exponential backoff: 2s, 4s, 8s (capped at 30s)
- Retry on: `Timeout`, `ConnectionError`, `429 Too Many Requests`
- Log each retry with backoff duration

**Implementation**: Apply to all HTTP requests in ieso, gridwatch, oeb sources.

**Beads**: open-data-coop-vy4

---

### 2. Gap Detection & Catch-Up Logic

**Problem**: Pipeline misses runs due to GitHub Actions downtime, quota limits, or manual stops. Data gaps go undetected.

**Solution**: Detect gaps on startup and backfill automatically.

```python
def detect_gaps(source: str, db_path: str) -> list[tuple[datetime, datetime]]:
    """Find missing time ranges based on source's expected frequency."""
    con = duckdb.connect(db_path, read_only=True)

    # Get actual data range
    result = con.execute(f"""
        SELECT
            MIN(timestamp) as first_ts,
            MAX(timestamp) as last_ts,
            COUNT(*) as record_count
        FROM raw.{source}_*
    """).fetchone()

    if not result or not result[1]:
        return []  # No data yet

    first, last, count = result

    # Calculate expected count based on source frequency
    expected = {
        "gridwatch": lambda: (last - first).total_seconds() / 3600,  # hourly
        "ieso": lambda: (last - first).total_seconds() / 3600,  # hourly
        "oeb": lambda: 1  # single table, no frequency
    }[source]()

    if count < expected * 0.95:  # Allow 5% tolerance
        # Find specific gaps with window functions
        gaps = con.execute(f"""
            SELECT
                timestamp as gap_start,
                LEAD(timestamp) OVER (ORDER BY timestamp) as gap_end,
                LEAD(timestamp) OVER (ORDER BY timestamp) - timestamp as gap_size
            FROM raw.{source}_*
            WHERE gap_size > INTERVAL '2 hours'  -- Ignore small gaps
        """).fetchall()
        return gaps

    return []
```

**Integration**:
1. Run gap detection before incremental updates
2. If gaps found, switch to targeted backfill mode
3. Log gap ranges and records added
4. Continue with normal incremental update

**Beads**: open-data-coop-1lu

---

### 3. Failure Tracking & Alerting

**Problem**: Silent failures accumulate. No notification when sources repeatedly fail.

**Solution**: Persistent failure log + automated alerting.

**Schema**:
```sql
CREATE TABLE pipeline_runs (
    run_id TEXT PRIMARY KEY,
    timestamp TIMESTAMP,
    source TEXT,
    status TEXT,  -- 'success', 'partial', 'failed'
    error_message TEXT,
    records_loaded INTEGER,
    duration_seconds REAL,
    git_commit TEXT,
    github_run_id TEXT
);
```

**Alerting Logic** (in GitHub Actions):
```bash
# After pipeline run, check for repeated failures
python scripts/check_failures.py

# check_failures.py pseudocode:
failures = db.query("""
    SELECT source, COUNT(*) as fail_count
    FROM pipeline_runs
    WHERE status = 'failed'
      AND timestamp > NOW() - INTERVAL '3 days'
    GROUP BY source
    HAVING fail_count >= 3
""")

if failures:
    for source, count in failures:
        # Create GitHub Issue with diagnostics
        gh issue create \
            --title "Pipeline Alert: ${source} failed ${count} times" \
            --body "Source ${source} has failed ${count} consecutive runs. Check logs..." \
            --label "pipeline-alert,${source}"
```

**Optional**: Webhook integration for Slack/email notifications.

**Beads**: open-data-coop-pe8

---

### 4. Data Quality Validation Gates

**Problem**: Bad data gets committed to data branch. No sanity checks before publish.

**Solution**: Validation step between dbt and git push.

**Validation Checks**:

```python
class ValidationResult:
    def __init__(self):
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def is_critical(self) -> bool:
        return len(self.errors) > 0

def validate_pipeline_output(db_path: str) -> ValidationResult:
    result = ValidationResult()
    con = duckdb.connect(db_path, read_only=True)

    # 1. Row count regression check
    current = con.execute("SELECT COUNT(*) FROM marts.fct_grid_generation").fetchone()[0]
    previous = get_previous_count()  # From last commit metadata
    if current < previous * 0.9:
        result.errors.append(f"Row count dropped {(1 - current/previous)*100:.1f}%")

    # 2. Schema drift detection
    current_schema = get_table_schema(con, "marts.fct_grid_generation")
    expected_schema = load_schema_snapshot()
    if current_schema != expected_schema:
        result.warnings.append("Schema drift detected")

    # 3. Null value percentage in critical columns
    for col in ["nuclear_mw", "total_mw", "timestamp"]:
        null_pct = con.execute(f"""
            SELECT COUNT_IF({col} IS NULL) * 100.0 / COUNT(*)
            FROM marts.fct_grid_generation
        """).fetchone()[0]
        if null_pct > 5:
            result.errors.append(f"{col} has {null_pct:.1f}% null values")

    # 4. Timestamp continuity (no multi-day gaps)
    gaps = con.execute("""
        SELECT
            timestamp,
            LEAD(timestamp) OVER (ORDER BY timestamp) - timestamp as gap
        FROM marts.fct_grid_generation
        WHERE gap > INTERVAL '2 days'
    """).fetchall()
    if gaps:
        result.warnings.append(f"Found {len(gaps)} multi-day timestamp gaps")

    # 5. Value range sanity checks
    invalid = con.execute("""
        SELECT COUNT(*) FROM marts.fct_grid_generation
        WHERE total_mw < 0 OR total_mw > 30000  -- Ontario max capacity ~25GW
    """).fetchone()[0]
    if invalid > 0:
        result.errors.append(f"{invalid} records with invalid total_mw values")

    return result
```

**Workflow Integration** (.github/workflows/pipeline.yml):
```yaml
- name: Validate data quality
  run: |
    python scripts/validate_data.py
    if [ $? -eq 2 ]; then
      echo "❌ CRITICAL validation errors - blocking push"
      exit 1
    elif [ $? -eq 1 ]; then
      echo "⚠️  Validation warnings - proceeding with caution"
    fi

- name: Push database to data branch
  if: success()  # Only runs if validation passes
  run: |
    ...
```

**Beads**: open-data-coop-r0y

---

### 5. Extended Freshness Checks

**Problem**: Current freshness logic only covers gridwatch. Other sources waste CI minutes on redundant runs.

**Solution**: Generalize freshness checks to all sources with appropriate thresholds.

```python
FRESHNESS_THRESHOLD: dict[str, timedelta] = {
    "gridwatch": timedelta(hours=1),      # Hourly updates
    "ieso": timedelta(hours=24),          # Daily check sufficient for monthly CSVs
    "oeb": timedelta(days=7),             # Weekly check for quarterly rate changes
}

FRESHNESS_QUERY: dict[str, str] = {
    "gridwatch": "SELECT MAX(timestamp) FROM raw.gridwatch_readings",
    "ieso": "SELECT MAX(timestamp) FROM raw.ieso_generation",
    "oeb": "SELECT MAX(effective_date) FROM raw.oeb_rates",
}

def is_fresh(source: str) -> bool:
    """Return True if DB has recent enough data for this source."""
    if source not in FRESHNESS_THRESHOLD:
        return False
    try:
        con = duckdb.connect(DB_PATH, read_only=True)
        result = con.execute(FRESHNESS_QUERY[source]).fetchone()
        con.close()
        if result and result[0]:
            age = datetime.now(timezone.utc) - result[0].replace(tzinfo=timezone.utc)
            is_fresh = age < FRESHNESS_THRESHOLD[source]
            if is_fresh:
                print(f"✓ {source} is fresh (age: {age}, threshold: {FRESHNESS_THRESHOLD[source]})")
            return is_fresh
    except Exception as e:
        print(f"⚠️  Freshness check failed for {source}: {e}")
    return False
```

**Benefits**:
- Reduces GitHub Actions minutes by ~30%
- Prevents rate limiting from over-polling
- Aligns check frequency with source update frequency

**Beads**: open-data-coop-07x

---

## Implementation Priority

### Phase 1 (High Impact, Low Effort)
1. **Retry logic** (vy4) - Immediate win on transient failures
2. **Extended freshness checks** (07x) - Reduces wasted CI runs

### Phase 2 (High Impact, Medium Effort)
3. **Failure tracking & alerting** (pe8) - Catch persistent problems early
4. **Gap detection** (1lu) - Automatic catch-up after downtime

### Phase 3 (Quality Assurance)
5. **Validation gates** (r0y) - Prevent bad data from being published

## Success Metrics

- **Reduce transient failures**: 90% of network errors auto-recover with retries
- **Eliminate silent gaps**: 0 undetected missing data periods > 1 day
- **Faster incident response**: <4 hours from 3rd failure to GitHub Issue creation
- **Prevent bad commits**: 100% of critical data quality issues blocked before push
- **Optimize CI usage**: 30% reduction in GitHub Actions minutes via freshness checks

## Testing Strategy

1. **Retry logic**: Mock network failures, verify exponential backoff timing
2. **Gap detection**: Create synthetic gaps, verify backfill triggers
3. **Alerting**: Simulate 3 consecutive failures, verify Issue creation
4. **Validation**: Inject bad data (nulls, negatives, gaps), verify blocking
5. **Freshness**: Fast-forward DB timestamps, verify skip logic

## Dependencies

- `tenacity` - Retry logic with exponential backoff
- `gh` CLI - GitHub Issue creation from workflow
- Existing: `duckdb`, `dlt`, `dbt`, `requests`

## Rollout Plan

1. Add new dependencies to pyproject.toml
2. Implement features in order (Phase 1 → 2 → 3)
3. Test locally with `--full-refresh` on historical data
4. Deploy to GitHub Actions with dry-run mode first
5. Monitor for 1 week, then enable all features

---

## References

- Beads: vy4 (retry), 1lu (gap detection), pe8 (alerting), r0y (validation), 07x (freshness)
- Current implementation: `pipeline.py`, `pipelines/*/source.py`, `.github/workflows/pipeline.yml`
- Related: Evidence dashboard reliability depends on upstream pipeline robustness
