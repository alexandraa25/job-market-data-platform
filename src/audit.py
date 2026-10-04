"""Persistent summaries and stage attempts. Never persist exception messages/secrets."""

import json
from sqlalchemy import text

METRICS = {
    "extracted",
    "accepted",
    "rejected",
    "inserted",
    "updated",
    "skipped",
    "quality_report_path",
}


def begin_stage(engine, run_id, stage, source):
    with engine.begin() as connection:
        connection.execute(
            text(
                """INSERT INTO job_runs(run_id, source, status, last_stage)
            VALUES (:run, :source, 'running', :stage) ON CONFLICT (run_id) DO NOTHING"""
            ),
            {"run": run_id, "source": source, "stage": stage},
        )
        connection.execute(
            text("SELECT run_id FROM job_runs WHERE run_id=:run FOR UPDATE"),
            {"run": run_id},
        )
        attempt = connection.execute(
            text("""SELECT COALESCE(MAX(attempt),0)+1 FROM job_run_attempts
            WHERE run_id=:run AND stage=:stage"""),
            {"run": run_id, "stage": stage},
        ).scalar_one()
        connection.execute(
            text("""INSERT INTO job_run_attempts(run_id,stage,attempt,status)
            VALUES (:run,:stage,:attempt,'running')"""),
            {"run": run_id, "stage": stage, "attempt": attempt},
        )
        reset = (
            ", extracted=NULL, accepted=NULL, rejected=NULL, inserted=NULL, updated=NULL, skipped=NULL, quality_report_path=NULL"
            if stage == "extract"
            else ""
        )
        connection.execute(
            text("""UPDATE job_runs SET status='running', finished_at=NULL,
            error_type=NULL, last_stage=:stage""" + reset + " WHERE run_id=:run"),
            {"run": run_id, "stage": stage},
        )
    return attempt


def finish_stage(engine, run_id, stage, attempt, metrics=None, error_type=None):
    metrics = metrics or {}
    if set(metrics) - METRICS:
        raise ValueError("Unknown audit metric")
    status = "failed" if error_type else "success"
    with engine.begin() as connection:
        connection.execute(
            text("""UPDATE job_run_attempts SET status=:status,
            finished_at=clock_timestamp(), metrics=CAST(:metrics AS jsonb), error_type=:error
            WHERE run_id=:run AND stage=:stage AND attempt=:attempt"""),
            {
                "status": status,
                "metrics": json.dumps(metrics),
                "error": error_type,
                "run": run_id,
                "stage": stage,
                "attempt": attempt,
            },
        )
        assignments = ", ".join(f"{key}=:{key}" for key in metrics)
        if assignments:
            assignments = ", " + assignments
        terminal = bool(error_type) or stage == "load"
        connection.execute(
            text(
                """UPDATE job_runs SET status=:status, last_stage=:stage,
            error_type=:error, finished_at="""
                + ("clock_timestamp()" if terminal else "NULL")
                + assignments
                + " WHERE run_id=:run"
            ),
            {
                "run": run_id,
                "stage": stage,
                "error": error_type,
                "status": status if terminal else "running",
                **metrics,
            },
        )
