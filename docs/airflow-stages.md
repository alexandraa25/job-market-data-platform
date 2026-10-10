# Airflow ETL stages

`job_market_etl` runs five BashOperator tasks in order:
`extract -> transform -> validate -> load -> spark_process`.

Each task runs `python -u src/stages.py <stage>`. The run ID is passed through
ETL_RUN_ID, preserving the inherited database environment. Artifacts live in
`data/runs/<sha256(run_id)>/` on the shared data mount:
- raw.json: collected and deduplicated API jobs, used by transform.
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

2026-10-05: Optional Azure Data Lake Gen2 raw upload is part of extract.
AZURE_UPLOAD_ENABLED defaults to false. When true, five AZURE_* settings from
.env are passed to the scheduler and manual ETL service. The service principal
needs Storage Blob Data Contributor on the existing private container.
The remote path is jobs/<sha256(run_id)>/raw.json. Same-run extraction overwrites
that path with its newly collected data; different runs use different paths.
Upload/configuration errors fail extract and use normal Airflow retries.
Downstream tasks still read local artifacts. azure_upload.json stores upload
path, byte count and SHA256; only extracted count is returned to business audit.
No credentials are written to artifacts. Rebuild scheduler and etl for SDK
changes and recreate services for environment changes; preserve volumes.
Verified manual run azure_integration_20261005_final: four successful tasks,
first attempts, 128 accepted, 0 rejected, 0 inserted, 3 updated, 125 skipped.
Remote download matched local raw bytes and SHA256. 53 regression tests passed
with isolated PostgreSQL and uploads disabled. Daily automatic Azure upload
has not yet been verified.

Rezultat demonstrație: scheduled__2026-10-05T10:26:00+00:00 a pornit automat la 13:26:00 Europe/Bucharest, run_type=scheduled, clear_number=0. Extract, transform, validate și load: success, try_number=1. Audit: 128 acceptate, 0 respinse, 0 inserted, 3 updated, 125 skipped. Fișierul Azure jobs/13fada25cf34bf7555e69de557c1eac4581f03f50a61708f5013b9634b516c9d/raw.json (867609 bytes) a fost descărcat și comparat byte cu byte cu raw local, inclusiv SHA256. Programarea ETL și monitorul au fost restabilite la 19:07, cu deadline 20:07. Nu s-a schimbat data calculatorului, nu s-a folosit Trigger/Clear, nu s-au șters volume. Aceasta confirmă programarea automată și uploadul cu sistemul activ; nu verifică funcționarea peste o noapte nesupravegheată.

2026-10-05: Optional standalone Spark processing is available through the spark Compose profile. It reads an existing Azure raw run and publishes versioned accepted/rejected Parquet with a completion manifest to processed. This does not add a task to the daily four-stage DAG. See README for CLI, local-only options and transfer/retention limitations.

2026-10-05: Spark is now orchestrated as the final BashOperator task in the
same DAG/run ID. Scheduler image includes Java 17 and PySpark 4.0.1.
python -u -m src.spark_process --airflow --run-id "$ETL_RUN_ID" reads Azure raw
and publishes processed when AZURE_UPLOAD_ENABLED=true; otherwise it reads
this run's local raw and only writes local Parquet. Retry=2, backoff, timeout=20m.
Clear only spark_process to retry publication without redoing PostgreSQL load.
When upstream stages are cleared, include Spark among downstream tasks.
job_runs remains the four-stage PostgreSQL audit; full five-task success is
Airflow DAG state. A Spark failure can occur after PostgreSQL commit and raises
pipeline_failed via the existing monitor. Daily confirmation requires core tasks
and every additional task present in metadata to succeed; historical four-task
runs remain supported. No Docker socket is mounted. No volume deletion.

Verified final manual Airflow run spark_orchestration_final_20261005: all five tasks success on try 1, 128 accepted / 0 rejected in Spark. Azure manifest and three Parquet files independently downloaded and verified. 59 regression tests passed on isolated PostgreSQL; offline --airflow mode verified. Spark standalone now uses UID 50000/group 0 matching Airflow; existing root-owned data/spark was corrected. Daily five-task scheduled execution is configured but not yet observed.


## Stare curenta si operare

La 8 octombrie 2026, cele trei DAG-uri sunt pe pauza si au schedule=None. Rularile programate 5–7 octombrie au reusit cu toate cele cinci task-uri si clear_number=0; cele din 6 si 7 au pornit tarziu. Programarile cron sunt pastrate comentate. Serviciul ETL independent are profil manual, deci pornirea normala Compose nu colecteaza date. Ghid complet: [OPERATIONS.md](OPERATIONS.md). Istoricul verificarilor de mai sus este pastrat.


DAG-ul separat `job_market_multi_source` foloseste `src.sources_workflow`: doua extrageri auditate -> process (transform/select/validate) -> load. Snapshot local implicit, programare oprita. Contractul DAG-ului original ramane neschimbat. Pentru proceduri si limite vezi MULTIPLE_SOURCES.md.
