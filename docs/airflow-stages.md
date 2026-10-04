# Airflow ETL stages

`job_market_etl` runs four BashOperator tasks in order:
`extract -> transform -> validate -> load`.

Each task runs `python -u src/stages.py <stage>`. The run ID is passed through
ETL_RUN_ID, preserving the inherited database environment. Artifacts live in
`data/runs/<sha256(run_id)>/` on the shared data mount:
- raw.json: API response, used by transform.
- transformed.json: typed Pandas table JSON preserving GUID strings, dates and numbers.
- validated.json: created only after successful validation; the only load input.

Validation partitions invalid rows into rejected.csv, writes quality_report.json, and loads accepted rows only. It rejects missing required text/publication dates, duplicate GUIDs, invalid salaries, reversed salary/date ranges, unknown roles and invalid skill flags. Missing salary and expiry date remain allowed. An empty accepted set fails validation. Existing quality reporting is
retained. Writes use temporary files followed by replacement. Artifacts are
retained for debugging; no automatic cleanup is configured.

To rerun a failed stage, clear that task and downstream tasks in Airflow UI.
When rerunning extract or transform, also clear validate and load so the
validated snapshot is regenerated. max_active_runs=1 serializes DAG runs.
The manual `python src/main.py` entry point remains available.

Verified from UI on 2026-10-03 at 19:41 Europe/Bucharest:
run manual__2026-10-03T16:41:14.680572+00:00 succeeded with all four tasks.
UPSERT: Inserted 8, Updated 6, Skipped 122. 15 tests passed, including artifact
roundtrip, run isolation and rejection before load. No Docker rebuild was
required because src and dags are mounted. Database volumes were preserved.
2026-10-04: All four tasks now have retries=2, retry_delay=1 minute, exponential backoff and max_retry_delay=5 minutes. The scheduled run was recovered using Clear for all tasks after host sleep caused an expired execution token; success at 15:32 Europe/Bucharest. Host/Docker must remain active for timely scheduling.

2026-10-04: CLI stages and main.py now use persistent job_runs/job_run_attempts via src/audit.py. Apply sql/migrations/001_run_audit.sql to existing business DBs. Retries preserve attempt history; forced termination may leave running audit rows until reconciliation.

2026-10-04: load now synchronizes companies, skills and job_skills in the same PostgreSQL transaction as jobs. Apply sql/migrations/002_model.sql after 001. Existing columns remain for CSV compatibility; existing historical jobs require a separate backfill, performed on the local DB.

job_market_audit_reconcile runs every five minutes, reading Airflow metadata with read-only transactions. It only reconciles existing running Airflow audits for terminal ETL runs older than two minutes; manual and active runs are ignored. Missing metrics are not reconstructed. Run reconcile_validation_20261004_2 succeeded with zero changes; controlled reconciliation cases and dimension updates are covered in the 38 passing tests.

2026-10-04: job_market_monitor polls every five minutes and persists terminal failure, rejected-percent and current-day scheduling alerts in pipeline_alerts. Apply additive migration 003_monitoring.sql after 002. MAX_REJECTED_PERCENT defaults to 10; only recorded accepted/rejected counts are evaluated. pipeline_daily_checks requires all four successful tasks and clear_number=0 for success_without_clear. Daily absence of success after 01:00 Europe/Bucharest alerts; host/Docker must stay active. Monitor checks ETL metadata from the last seven days, does not backfill daily checks, and does not send external notifications. See the central README for SQL queries and verification limits.

2026-10-04: Daily ETL schedule changed to 7 19 * * * (19:07 Europe/Bucharest). Monitor ETL_DAILY_TIME is 19:07, with a 60-minute success deadline (20:07). The schedule persists until explicitly changed.
