from datetime import timedelta

import pendulum
from airflow.sdk import DAG
from airflow.providers.standard.operators.bash import BashOperator


with DAG(
    dag_id="job_market_etl",
    description="Job Market ETL Pipeline",
    start_date=pendulum.datetime(2026, 10, 1, tz="Europe/Bucharest"),
    schedule="@daily",
    catchup=False,
    max_active_runs=1,
    tags=["etl", "data-engineering", "job-market"],
) as dag:
    run_job_market_pipeline = BashOperator(
        task_id="run_job_market_pipeline",
        bash_command="exec python -u src/main.py",
        cwd="/opt/airflow/project",
        do_xcom_push=False,
        skip_on_exit_code=None,
        execution_timeout=timedelta(minutes=20),
    )
