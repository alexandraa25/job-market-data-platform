import os
from datetime import timedelta
import pendulum
from airflow.sdk import DAG
from airflow.providers.standard.operators.bash import BashOperator

with DAG(
    dag_id="job_market_monitor",
    start_date=pendulum.datetime(2026, 10, 1, tz="Europe/Bucharest"),
    schedule="*/5 * * * *",
    catchup=False,
    max_active_runs=1,
    tags=["monitoring", "job-market"],
) as dag:
    check = BashOperator(
        task_id="check",
        bash_command="exec python -u src/monitor.py",
        cwd="/opt/airflow/project",
        append_env=True,
        do_xcom_push=False,
        env={
            "RECONCILE_METADATA_URL": "postgresql+psycopg://airflow:airflow@airflow-db:5432/airflow",
            "ETL_DAILY_TIME": "19:07",
            "MAX_REJECTED_PERCENT": os.getenv("MAX_REJECTED_PERCENT", "10"),
        },
        retries=2,
        retry_delay=timedelta(minutes=1),
        execution_timeout=timedelta(minutes=3),
    )
