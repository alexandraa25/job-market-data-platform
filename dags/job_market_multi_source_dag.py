from datetime import timedelta
import pendulum
from airflow.sdk import DAG, Param
from airflow.providers.standard.operators.bash import BashOperator

with DAG(
    dag_id="job_market_multi_source",
    description="Audited Himalayas + Arbeitnow extraction, common quality and atomic load",
    start_date=pendulum.datetime(2026, 10, 1, tz="Europe/Bucharest"),
    schedule=None,  # OPRIT: doar demonstratii manuale; fara consum automat.
    catchup=False,
    max_active_runs=1,
    params={
        "mode": Param(
            "snapshot",
            enum=["snapshot", "live"],
            description="Snapshot local implicit; live apeleaza API-urile publice.",
        )
    },
    tags=["multi-source", "manual"],
) as dag:
    tasks = {}
    for stage in ("extract_himalayas", "extract_arbeitnow", "process", "load"):
        tasks[stage] = BashOperator(
            task_id=stage,
            bash_command=f"exec python -u -m src.sources_workflow {stage}",
            cwd="/opt/airflow/project",
            env={
                "MULTI_RUN_ID": "{{ run_id }}",
                "MULTI_ATTEMPT": "{{ ti.try_number }}",
                "MULTI_MODE": "{{ params.mode }}",
            },
            append_env=True,
            do_xcom_push=False,
            skip_on_exit_code=None,
            retries=2,
            retry_delay=timedelta(minutes=1),
            execution_timeout=timedelta(minutes=20),
        )
    (
        [tasks["extract_himalayas"], tasks["extract_arbeitnow"]]
        >> tasks["process"]
        >> tasks["load"]
    )
