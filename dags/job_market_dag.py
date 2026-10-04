from datetime import timedelta

import pendulum
from airflow.sdk import DAG
from airflow.providers.standard.operators.bash import BashOperator

with DAG(
    dag_id="job_market_etl",
    description="Job Market ETL: extract → transform → validate → load",
    start_date=pendulum.datetime(2026, 10, 1, tz="Europe/Bucharest"),
    schedule="7 19 * * *",
    catchup=False,
    max_active_runs=1,
    tags=["etl", "data-engineering", "job-market"],
) as dag:
    stages = {}
    for stage in ("extract", "transform", "validate", "load"):
        stages[stage] = BashOperator(
            task_id=stage,
            bash_command=f"exec python -u src/stages.py {stage}",
            env={"ETL_RUN_ID": "{{ run_id }}"},
            append_env=True,
            cwd="/opt/airflow/project",
            do_xcom_push=False,
            skip_on_exit_code=None,
            execution_timeout=timedelta(minutes=20),
            retries=2,
            retry_delay=timedelta(minutes=1),
            retry_exponential_backoff=True,
            max_retry_delay=timedelta(minutes=5),
        )
    stages["extract"] >> stages["transform"] >> stages["validate"] >> stages["load"]
