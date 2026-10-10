"""Explicit manual loading of a validated multi-source snapshot into PostgreSQL."""

import argparse
import json
from uuid import uuid4
from collections import Counter
from sqlalchemy import text
from pathlib import Path

import pandas as pd
from src.load import create_db_engine, upsert_jobs
from src.quality import assess_jobs


def load_snapshot(path, engine, workflow_run_id=None):
    rows = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(rows, list) or not rows:
        raise ValueError("Snapshot must contain a nonempty list of accepted jobs")
    frame = pd.DataFrame(rows)
    if (
        "source" not in frame
        or frame.source.isna().any()
        or frame.source.astype(str).str.strip().eq("").any()
    ):
        raise ValueError("Snapshot requires explicit nonempty source")
    counts = Counter(frame.source)
    run_id = "source-load-" + uuid4().hex
    with engine.begin() as connection:
        for source, count in counts.items():
            connection.execute(
                text(
                    "INSERT INTO source_load_runs(run_id,source,status,input_rows,workflow_run_id) VALUES (:run,:source,'running',:count,:workflow)"
                ),
                {
                    "run": run_id,
                    "source": source,
                    "count": count,
                    "workflow": workflow_run_id,
                },
            )
    accepted = rejected = None
    try:
        for column in ("pubDate", "expiryDate"):
            frame[column] = pd.to_datetime(frame[column], errors="raise")
        accepted, rejected, quality = assess_jobs(frame)
        if len(rejected):
            raise ValueError("Snapshot no longer passes quality checks; no rows loaded")
        by_source = {}
        with engine.begin() as connection:
            metrics = upsert_jobs(
                accepted, engine, connection=connection, by_source=by_source
            )
            for source, count in counts.items():
                connection.execute(
                    text(
                        "UPDATE source_load_runs SET status='success',finished_at=clock_timestamp(),accepted=:count,rejected=0,inserted=:inserted,updated=:updated,skipped=:skipped WHERE run_id=:run AND source=:source"
                    ),
                    {
                        "run": run_id,
                        "source": source,
                        "count": count,
                        **by_source[source],
                    },
                )
        return {
            "run_id": run_id,
            "quality": quality,
            "load": metrics,
            "by_source": by_source,
        }
    except Exception as exc:
        # Only persist exception type, never its potentially sensitive message.
        with engine.begin() as connection:
            for source in counts:
                connection.execute(
                    text(
                        "UPDATE source_load_runs SET status='failed',finished_at=clock_timestamp(),error_type=:error,accepted=:accepted,rejected=:rejected,inserted=0,updated=0,skipped=0 WHERE run_id=:run AND source=:source"
                    ),
                    {
                        "run": run_id,
                        "source": source,
                        "error": type(exc).__name__,
                        "accepted": (
                            int(accepted.source.eq(source).sum())
                            if accepted is not None
                            else None
                        ),
                        "rejected": (
                            int(rejected.source.eq(source).sum())
                            if rejected is not None
                            else None
                        ),
                    },
                )
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--accepted", required=True)
    args = parser.parse_args()
    engine = create_db_engine()
    try:
        print(json.dumps(load_snapshot(args.accepted, engine)))
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
