"""Read Airflow metadata; reconcile only terminal DAG runs, never active runs."""
import logging
import os
from sqlalchemy import create_engine, text
try:
    from .load import create_db_engine
except ImportError:
    from load import create_db_engine


def reconcile(business, metadata):
    changed = 0
    with business.connect() as connection:
        candidates = connection.execute(text("SELECT run_id FROM job_runs WHERE source='airflow' AND status='running'")).scalars().all()
    for run_id in candidates:
        with metadata.connect() as connection:
            run = connection.execute(text("""SELECT state,end_date FROM dag_run
                WHERE dag_id='job_market_etl' AND run_id=:run AND state IN ('success','failed')
                AND end_date < CURRENT_TIMESTAMP - INTERVAL '2 minutes'"""), {"run": run_id}).mappings().first()
            if not run:
                continue
            tasks = dict(connection.execute(text("""SELECT task_id,state FROM task_instance
                WHERE dag_id='job_market_etl' AND run_id=:run AND map_index=-1"""), {"run": run_id}).all())
        with business.begin() as connection:
            current = connection.execute(text("SELECT status FROM job_runs WHERE run_id=:run FOR UPDATE"), {"run": run_id}).scalar_one()
            if current != 'running':
                continue
            # A retry/clear started since the metadata read: leave the run alone.
            with metadata.connect() as check:
                still_terminal = check.execute(text("SELECT state FROM dag_run WHERE dag_id='job_market_etl' AND run_id=:run"), {"run": run_id}).scalar_one_or_none()
            if still_terminal != run['state']:
                continue
            for stage, state in tasks.items():
                if state not in ('success', 'failed', 'upstream_failed'):
                    continue
                connection.execute(text("""UPDATE job_run_attempts SET status=:status,
                    finished_at=:end, error_type=:error WHERE run_id=:run AND stage=:stage AND status='running'"""),
                    {"run": run_id, "stage": stage, "end": run['end_date'],
                     "status": 'success' if state == 'success' else 'failed',
                     "error": None if state == 'success' else 'AirflowReconciledFailure'})
            connection.execute(text("""UPDATE job_runs SET status=:state,finished_at=:end,
                error_type=:error,reconciled_at=clock_timestamp() WHERE run_id=:run"""),
                {"run": run_id, "state": run['state'], "end": run['end_date'],
                 "error": None if run['state']=='success' else 'AirflowReconciledFailure'})
            changed += 1
    return changed


if __name__ == '__main__':
    business = create_db_engine()
    metadata = create_engine(os.environ.get('RECONCILE_METADATA_URL') or os.environ['AIRFLOW__DATABASE__SQL_ALCHEMY_CONN'], connect_args={'options': '-cdefault_transaction_read_only=on'})
    try:
        print(f"Reconciled runs: {reconcile(business, metadata)}")
    finally:
        business.dispose()
        metadata.dispose()
