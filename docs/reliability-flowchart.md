# Pipeline Reliability Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                    GitHub Actions Scheduled Run                  │
│                    (hourly/daily/weekly)                         │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  Step 1: Restore Database from Data Branch                       │
│  ✓ Fallback: Start fresh if restore fails                       │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  Step 2: Freshness Check (NEW - extends to all sources)         │
│  ✓ Skip if data age < threshold (gridwatch: 1h, ieso: 1d, oeb: 7d) │
│  ✓ Saves ~30% CI minutes on redundant runs                      │
└────────────────────────────┬────────────────────────────────────┘
                             │
                    ┌────────┴────────┐
                    │ Fresh? Yes      │ → Skip source, continue to next
                    └────────┬────────┘
                             │ No
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  Step 3: Gap Detection (NEW)                                     │
│  ✓ Query: expected records vs actual based on frequency         │
│  ✓ Identify missing time ranges                                 │
└────────────────────────────┬────────────────────────────────────┘
                             │
                    ┌────────┴────────┐
                    │ Gaps found?     │
                    └────────┬────────┘
                  Yes │              │ No
                      ▼              ▼
        ┌──────────────────┐    ┌─────────────────┐
        │ Backfill Mode    │    │ Incremental Mode │
        │ - Target gaps    │    │ - Fetch new data │
        │ - Log recovered  │    │ - Merge into DB  │
        └────────┬─────────┘    └────────┬─────────┘
                 │                       │
                 └───────────┬───────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  Step 4: Extract (dlt) - with Retry Logic (NEW)                 │
│  For each source (ieso, gridwatch, oeb):                        │
│    ┌─────────────────────────────────────────────┐             │
│    │  HTTP Request                                │             │
│    │  ├─ Success → Continue                       │             │
│    │  └─ Failure → Retry with exponential backoff│             │
│    │      • Attempt 1: wait 2s                    │             │
│    │      • Attempt 2: wait 4s                    │             │
│    │      • Attempt 3: wait 8s                    │             │
│    │      • Max: 30s between attempts             │             │
│    │      • Retry on: Timeout, ConnectionError, 429│            │
│    └─────────────────────────────────────────────┘             │
│  ✓ If source fails after retries: log + continue (not critical) │
│  ✓ Record run metadata (success/fail, records, duration)        │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  Step 5: Transform (dbt)                                         │
│  ✓ Staging models: stg_ieso_generation, stg_gridwatch, stg_oeb  │
│  ✓ Marts: fct_grid_generation, fct_co2_intensity                │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  Step 6: Data Quality Validation (NEW)                           │
│  Critical Checks (block push if fail):                           │
│    • Row count regression > 10%                                  │
│    • Null values > 5% in critical columns                        │
│    • Invalid value ranges (e.g., total_mw < 0)                   │
│  Warnings (log but continue):                                    │
│    • Schema drift detected                                       │
│    • Multi-day timestamp gaps                                    │
└────────────────────────────┬────────────────────────────────────┘
                             │
                    ┌────────┴────────┐
                    │ Critical errors? │
                    └────────┬─────────┘
                  Yes │              │ No
                      ▼              ▼
        ┌──────────────────┐    ┌─────────────────┐
        │ FAIL Pipeline    │    │ PASS - Continue │
        │ - Block push     │    │                 │
        │ - Alert in logs  │    │                 │
        │ - Create Issue   │    │                 │
        └──────────────────┘    └────────┬─────────┘
                                         │
                                         ▼
┌─────────────────────────────────────────────────────────────────┐
│  Step 7: Record Run in Failure Log (NEW)                         │
│  Write to pipeline_runs table:                                   │
│    • timestamp, source, status, error_msg, records_loaded        │
│    • git_commit, github_run_id, duration_seconds                 │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  Step 8: Check for Repeated Failures (NEW)                       │
│  Query: sources with 3+ failures in last 3 days                  │
│  Action: Create GitHub Issue with diagnostics                    │
│    • Title: "Pipeline Alert: {source} failed 3 times"            │
│    • Body: Error logs, timestamps, recent changes                │
│    • Labels: pipeline-alert, {source}                            │
│  Optional: Send Slack/email notification                         │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  Step 9: Push Database to Data Branch                            │
│  ✓ Commit message includes: timestamp, sources, mode             │
│  ✓ Single-commit force-push to orphan branch (no history growth)│
└─────────────────────────────────────────────────────────────────┘


═══════════════════════════════════════════════════════════════════

                         Error Scenarios

Scenario 1: Transient Network Failure
  1. HTTP request times out
  2. Retry logic kicks in (wait 2s)
  3. Second attempt succeeds
  4. Pipeline continues normally
  Result: ✓ Automatic recovery, no human intervention

Scenario 2: GitHub Actions Downtime (12 hours)
  1. Scheduler misses 12 hourly runs
  2. Next run detects 12-hour gap
  3. Gap detection triggers backfill mode
  4. Pipeline fetches missing 12 hours
  5. Continues with incremental update
  Result: ✓ Data continuity maintained automatically

Scenario 3: IESO Blocks Datacenter IP (3 days)
  1. IESO source fails (403 Forbidden)
  2. Retry logic exhausts attempts
  3. Source logs warning, pipeline continues
  4. Run recorded as "partial" (other sources OK)
  5. After 3 consecutive failures, GitHub Issue created
  6. Human investigates, runs locally to backfill
  Result: ✓ Alerting catches persistent issue early

Scenario 4: Bad Data Pushed (schema change)
  1. dlt extracts data with new unexpected column
  2. dbt transforms complete successfully
  3. Validation detects schema drift
  4. Critical error: Push blocked
  5. GitHub Actions fails with clear error message
  6. Developer reviews and updates schema intentionally
  Result: ✓ Bad data prevented from reaching production

═══════════════════════════════════════════════════════════════════

                    Monitoring Dashboard (Future)

  ┌─────────────────────────────────────────────────────────────┐
  │  Pipeline Health (last 7 days)                              │
  ├─────────────────────────────────────────────────────────────┤
  │  Source       Success Rate    Last Success    Gaps Detected │
  │  ───────────  ────────────    ────────────    ───────────── │
  │  gridwatch    168/168 (100%)  2026-07-07 13:00  0           │
  │  ieso         7/7 (100%)      2026-07-07 09:00  0           │
  │  oeb          1/1 (100%)      2026-07-07 08:00  0           │
  ├─────────────────────────────────────────────────────────────┤
  │  Data Quality Checks                                        │
  │  • Row count: 139,956 (+124 from last run)                 │
  │  • Timestamp range: 2010-01-01 to 2026-07-07               │
  │  • Null percentage: 0.02% (within threshold)               │
  │  • Value ranges: All within expected bounds                │
  └─────────────────────────────────────────────────────────────┘
```
