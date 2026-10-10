"""Manual multi-source workflow with audited extraction and fail-closed loading."""

import argparse
import hashlib
import json
import os
from pathlib import Path
from sqlalchemy import text
from src.load import create_db_engine
from src.extract import extract_jobs
from src.sources.arbeitnow import fetch_jobs
from src.sources_pilot import pilot
from src.sources_load import load_snapshot


def run_folder(run_id):
    return Path("data/sources/runs") / hashlib.sha256(run_id.encode()).hexdigest()


def extract_source(engine, run_id, source, attempt, mode="snapshot"):
    folder = run_folder(run_id)
    folder.mkdir(parents=True, exist_ok=True)
    destination = folder / (source + ".json")
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO source_extraction_attempts(run_id,source,attempt,mode,status) VALUES (:run,:source,:attempt,:mode,'running')"
            ),
            {"run": run_id, "source": source, "attempt": attempt, "mode": mode},
        )
    try:
        if mode == "live":
            payload = (
                extract_jobs() if source == "himalayas" else fetch_jobs(max_pages=3)
            )
        elif source == "himalayas":
            payload = json.loads(
                Path("data/sources/input/himalayas.json").read_text(
                    encoding="utf-8-sig"
                )
            )
        else:
            rows = {}
            for name in ("page-1.json", "page-2.json", "page-3.json"):
                for row in json.loads(
                    (Path("data/sources/input") / name).read_text(encoding="utf-8-sig")
                )["data"]:
                    rows.setdefault(row["slug"], row)
            payload = {"data": list(rows.values())}
        key = "jobs" if source == "himalayas" else "data"
        if not isinstance(payload.get(key), list) or not payload[key]:
            raise ValueError("Empty or invalid extraction; downstream blocked")
        temporary = folder / f"{source}.{attempt}.tmp"
        temporary.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        temporary.replace(destination)
        with engine.begin() as connection:
            connection.execute(
                text(
                    "UPDATE source_extraction_attempts SET status='success',finished_at=clock_timestamp(),extracted=:count,snapshot_path=:path WHERE run_id=:run AND source=:source AND attempt=:attempt"
                ),
                {
                    "run": run_id,
                    "source": source,
                    "attempt": attempt,
                    "count": len(payload[key]),
                    "path": str(destination),
                },
            )
        return destination
    except Exception as exc:
        with engine.begin() as connection:
            connection.execute(
                text(
                    "UPDATE source_extraction_attempts SET status='failed',finished_at=clock_timestamp(),error_type=:error WHERE run_id=:run AND source=:source AND attempt=:attempt"
                ),
                {
                    "run": run_id,
                    "source": source,
                    "attempt": attempt,
                    "error": type(exc).__name__,
                },
            )
        raise


def process_sources(engine, run_id, attempt):
    with engine.connect() as connection:
        for source in ("himalayas", "arbeitnow"):
            status = connection.execute(
                text(
                    "SELECT status FROM source_extraction_attempts WHERE run_id=:run AND source=:source ORDER BY attempt DESC LIMIT 1"
                ),
                {"run": run_id, "source": source},
            ).scalar_one_or_none()
            if status != "success":
                raise ValueError("Both latest source attempts must succeed")
    folder = run_folder(run_id)
    output = folder / f"processed-{attempt}"
    return pilot(
        json.loads((folder / "himalayas.json").read_text(encoding="utf-8")),
        [json.loads((folder / "arbeitnow.json").read_text(encoding="utf-8"))],
        output,
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "stage", choices=["extract_himalayas", "extract_arbeitnow", "process", "load"]
    )
    args = parser.parse_args()
    run_id = os.environ["MULTI_RUN_ID"]
    attempt = int(os.environ.get("MULTI_ATTEMPT", "1"))
    mode = os.environ.get("MULTI_MODE", "snapshot")
    if mode not in ("snapshot", "live"):
        raise ValueError("Unknown source mode")
    engine = create_db_engine()
    try:
        if args.stage.startswith("extract_"):
            print(
                extract_source(
                    engine, run_id, args.stage.removeprefix("extract_"), attempt, mode
                )
            )
        elif args.stage == "process":
            print(json.dumps(process_sources(engine, run_id, attempt)))
        else:
            # Select newest successful processing output; Airflow upstream gates load.
            outputs = sorted(
                run_folder(run_id).glob("processed-*/accepted.json"),
                key=lambda p: int(p.parent.name.split("-")[-1]),
            )
            if not outputs:
                raise ValueError("No accepted snapshot for this run")
            print(
                json.dumps(load_snapshot(outputs[-1], engine, workflow_run_id=run_id))
            )
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
