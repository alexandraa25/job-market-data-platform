import pendulum
from airflow.sdk import DAG
from airflow.providers.standard.operators.bash import BashOperator

with DAG(
    dag_id="job_market_audit_reconcile",
    start_date=pendulum.datetime(2026, 10, 1, tz="Europe/Bucharest"),
    schedule="*/5 * * * *",
    catchup=False,
    max_active_runs=1,
    tags=["audit"],
) as dag:
    reconcile = BashOperator(
        task_id="reconcile",
        bash_command="exec python -u src/reconcile.py",
        cwd="/opt/airflow/project",
        do_xcom_push=False,
        env={
            "RECONCILE_METADATA_URL": "postgresql+psycopg://airflow:airflow@airflow-db:5432/airflow"
        },
        append_env=True,
    )
