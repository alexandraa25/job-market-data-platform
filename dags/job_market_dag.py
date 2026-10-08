from datetime import timedelta

import pendulum
from airflow.sdk import DAG
from airflow.providers.standard.operators.bash import BashOperator

with DAG(
    dag_id="job_market_etl",
    description="Job Market ETL: extract → transform → validate → load → spark_process",
    start_date=pendulum.datetime(2026, 10, 1, tz="Europe/Bucharest"),
    # OPRIT: fara rulari automate; executarea manuala ramane disponibila.
    schedule=None,
    # PORNIT: comenteaza schedule=None si decomenteaza linia urmatoare.
    # schedule="7 19 * * *",  # zilnic la 19:07 Europe/Bucharest
    # Dupa reactivare, activeaza si DAG-ul din UI Airflow (Unpause).
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

    spark_process = BashOperator(
        task_id="spark_process",
        bash_command='exec python -u -m src.spark_process --airflow --run-id "$ETL_RUN_ID"',
        env={"ETL_RUN_ID": "{{ run_id }}", "SPARK_LOCAL_IP": "127.0.0.1"},
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
    stages["load"] >> spark_process
