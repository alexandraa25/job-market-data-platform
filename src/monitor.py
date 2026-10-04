"""Poll terminal ETL runs and persist local alerts; no external notifications."""

import json
import logging
import math
import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from sqlalchemy import create_engine, text

try:
    from .load import create_db_engine
except ImportError:
    from load import create_db_engine

logger = logging.getLogger(__name__)
STAGES = ("extract", "transform", "validate", "load")


def validate_threshold(value):
    threshold = float(value)
    if not math.isfinite(threshold) or not 0 <= threshold <= 100:
        raise ValueError("MAX_REJECTED_PERCENT must be between 0 and 100")
    return threshold


def decisions(run, audit, threshold):
    if run["state"] not in ("success", "failed"):
        return []  # Do not alert on a failed attempt while Airflow can still retry.
    result = [
        ("pipeline_failed", run["state"] == "failed", {"airflow_state": run["state"]})
    ]
    if audit and audit["accepted"] is not None and audit["rejected"] is not None:
        total = audit["accepted"] + audit["rejected"]
        percent = 100.0 * audit["rejected"] / total if total else 0
        result.append(
            (
                "rejected_rows",
                percent > threshold,
                {
                    "accepted": audit["accepted"],
                    "rejected": audit["rejected"],
                    "rejected_percent": percent,
                    "threshold_percent": threshold,
                },
            )
        )
    return result


def persist_alert(connection, run_id, kind, active, details):
    connection.execute(
        text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"),
        {"key": run_id + "|" + kind},
    )
    previous = connection.execute(
        text(
            "SELECT status FROM pipeline_alerts WHERE run_id=:run AND kind=:kind FOR UPDATE"
        ),
        {"run": run_id, "kind": kind},
    ).scalar_one_or_none()
    args = {"run": run_id, "kind": kind, "details": json.dumps(details)}
    if active:
        connection.execute(
            text(
                """INSERT INTO pipeline_alerts(run_id,kind,status,details)
          VALUES(:run,:kind,'open',CAST(:details AS jsonb)) ON CONFLICT(run_id,kind) DO UPDATE
          SET status='open',last_seen_at=clock_timestamp(),resolved_at=NULL,details=EXCLUDED.details"""
            ),
            args,
        )
        return (
            "opened"
            if previous is None
            else "reopened" if previous == "resolved" else None
        )
    if previous == "open":
        connection.execute(
            text(
                """UPDATE pipeline_alerts SET status='resolved',last_seen_at=clock_timestamp(),
          resolved_at=clock_timestamp(),details=CAST(:details AS jsonb) WHERE run_id=:run AND kind=:kind"""
            ),
            args,
        )
        return "resolved"
    return None


def check_daily(runs, tasks, now, grace_minutes=60):
    local = now.astimezone(ZoneInfo("Europe/Bucharest"))
    due = local.replace(hour=0, minute=0, second=0, microsecond=0)
    candidates = [
        r
        for r in runs
        if r["run_type"] == "scheduled"
        and r["run_after"] >= due
        and r["run_after"] < due + timedelta(days=1)
    ]
    run = max(candidates, key=lambda r: r["run_after"]) if candidates else None
    state = run["state"] if run else "missing"
    all_success = bool(run) and all(
        tasks.get(run["run_id"], {}).get(s) == "success" for s in STAGES
    )
    success = state == "success" and all_success
    details = {
        "run_id": run["run_id"] if run else None,
        "state": state,
        "clear_number": run["clear_number"] if run else None,
        "all_tasks_success": all_success,
        "grace_minutes": grace_minutes,
    }
    return (
        local.date(),
        not success and local >= due + timedelta(minutes=grace_minutes),
        success and run["clear_number"] == 0,
        details,
    )


def monitor(business, metadata, threshold=10, now=None):
    threshold = validate_threshold(threshold)
    now = now or datetime.now(ZoneInfo("Europe/Bucharest"))
    with metadata.connect() as c:
        runs = [
            dict(r)
            for r in c.execute(
                text("""SELECT run_id,state,run_type,run_after,clear_number
            FROM dag_run WHERE dag_id='job_market_etl' AND run_after>=:since"""),
                {"since": now - timedelta(days=7)},
            ).mappings()
        ]
        task_rows = c.execute(
            text(
                """SELECT ti.run_id,ti.task_id,ti.state FROM task_instance ti
            JOIN dag_run dr ON dr.dag_id=ti.dag_id AND dr.run_id=ti.run_id
            WHERE ti.dag_id='job_market_etl' AND ti.map_index=-1 AND dr.run_after>=:since"""
            ),
            {"since": now - timedelta(days=7)},
        ).all()
    tasks = {}
    for run_id, stage, state in task_rows:
        tasks.setdefault(run_id, {})[stage] = state
    transitions = []
    with business.begin() as c:
        for run in runs:
            audit = (
                c.execute(
                    text("SELECT accepted,rejected FROM job_runs WHERE run_id=:run"),
                    {"run": run["run_id"]},
                )
                .mappings()
                .first()
            )
            for kind, active, details in decisions(run, audit, threshold):
                transition = persist_alert(c, run["run_id"], kind, active, details)
                if transition:
                    transitions.append((run["run_id"], kind, transition))
        day, late, confirmed, details = check_daily(runs, tasks, now)
        transition = None
        if late or (details["state"] == "success" and details["all_tasks_success"]):
            transition = persist_alert(
                c,
                "scheduled_day:" + day.isoformat(),
                "daily_missing_success",
                late,
                details,
            )
        if transition:
            transitions.append(
                (
                    "scheduled_day:" + day.isoformat(),
                    "daily_missing_success",
                    transition,
                )
            )
        # Before the grace deadline, leave a prior alert alone unless success is observed.
        c.execute(
            text(
                """INSERT INTO pipeline_daily_checks(expected_day,run_id,state,success_without_clear,details)
            VALUES(:day,:run,:state,:confirmed,CAST(:details AS jsonb)) ON CONFLICT(expected_day) DO UPDATE
            SET checked_at=clock_timestamp(),run_id=EXCLUDED.run_id,state=EXCLUDED.state,
            success_without_clear=EXCLUDED.success_without_clear,details=EXCLUDED.details"""
            ),
            {
                "day": day,
                "run": details["run_id"],
                "state": details["state"],
                "confirmed": confirmed,
                "details": json.dumps(details),
            },
        )
    for run, kind, transition in transitions:
        logger.warning("ALERT %s | %s | %s", transition, kind, run)
    logger.info(
        "Daily check: %s | state=%s | success_without_clear=%s",
        day,
        details["state"],
        confirmed,
    )
    return transitions


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    business = create_db_engine()
    metadata = create_engine(
        os.environ["RECONCILE_METADATA_URL"],
        connect_args={"options": "-cdefault_transaction_read_only=on"},
    )
    try:
        print(
            "Alert transitions:",
            len(monitor(business, metadata, os.getenv("MAX_REJECTED_PERCENT", "10"))),
        )
    finally:
        business.dispose()
        metadata.dispose()
