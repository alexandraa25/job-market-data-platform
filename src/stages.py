"""Run one ETL stage; exchange typed JSON artifacts within a DAG run."""

import argparse
import hashlib
import json
import logging
import os
from pathlib import Path

import pandas as pd

try:
    from .audit import begin_stage, finish_stage
    from .quality import validate_and_save
    from .extract import extract_jobs, save_raw_data
    from .transform import (
        transform_jobs,
        normalize_list_columns,
        add_primary_role,
        extract_skills,
        validate_jobs,
        save_processed_data,
    )
    from .load import create_db_engine, test_connection, upsert_jobs
    from .logger_config import setup_logger
except ImportError:
    from audit import begin_stage, finish_stage
    from quality import validate_and_save
    from extract import extract_jobs, save_raw_data
    from transform import (
        transform_jobs,
        normalize_list_columns,
        add_primary_role,
        extract_skills,
        validate_jobs,
        save_processed_data,
    )
    from load import create_db_engine, test_connection, upsert_jobs
    from logger_config import setup_logger

logger = logging.getLogger(__name__)


def run_directory(run_id):
    # Hash instead of inserting user-controlled run IDs into filesystem paths.
    return Path("data/runs") / hashlib.sha256(run_id.encode()).hexdigest()


def write_frame(df, path):
    temporary = path.with_suffix(".tmp")
    df.to_json(
        temporary,
        orient="table",
        date_format="iso",
        date_unit="ns",
        double_precision=15,
        index=False,
    )
    temporary.replace(path)


def _execute_stage(stage, run_id):
    directory = run_directory(run_id)
    directory.mkdir(parents=True, exist_ok=True)
    raw = directory / "raw.json"
    transformed = directory / "transformed.json"
    validated = directory / "validated.json"
    logger.info("Stage %s | run %s | artifacts %s", stage, run_id, directory)
    if stage == "extract":
        data = extract_jobs(max_jobs_per_query=40)
        temporary = raw.with_suffix(".tmp")
        temporary.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        temporary.replace(raw)
        save_raw_data(data)
        return {"extracted": len(data["jobs"])}
    elif stage == "transform":
        data = json.loads(raw.read_text(encoding="utf-8"))
        df = extract_skills(
            add_primary_role(normalize_list_columns(transform_jobs(data)))
        )
        write_frame(df, transformed)
    elif stage == "validate":
        # Remove any previous approval before revalidating this run.
        validated.unlink(missing_ok=True)
        df = pd.read_json(transformed, orient="table")
        validate_jobs(df)
        df = validate_and_save(df, directory)
        write_frame(df, validated)
        report = json.loads((directory / "quality_report.json").read_text())
        return {
            "accepted": report["accepted"],
            "rejected": report["rejected"],
            "quality_report_path": str(directory / "quality_report.json"),
        }
    elif stage == "load":
        df = pd.read_json(validated, orient="table")
        engine = create_db_engine()
        try:
            test_connection(engine)
            metrics = upsert_jobs(df, engine)
            save_processed_data(df)
            return metrics
        finally:
            engine.dispose()
    else:
        raise ValueError(f"Unknown stage: {stage}")
    logger.info("Stage %s completed successfully", stage)


def run_stage(stage, run_id, audit=False, source="airflow"):
    if not audit:
        return _execute_stage(stage, run_id)
    engine = create_db_engine()
    try:
        attempt = begin_stage(engine, run_id, stage, source)
        try:
            metrics = _execute_stage(stage, run_id) or {}
        except Exception as error:
            metrics = {}
            report_path = run_directory(run_id) / "quality_report.json"
            if stage == "validate" and report_path.exists():
                report = json.loads(report_path.read_text())
                metrics = {
                    "accepted": report["accepted"],
                    "rejected": report["rejected"],
                    "quality_report_path": str(report_path),
                }
            try:
                finish_stage(
                    engine, run_id, stage, attempt, metrics, type(error).__name__
                )
            except Exception:
                logger.error(
                    "Could not persist failure audit for run %s stage %s", run_id, stage
                )
            raise
        finish_stage(engine, run_id, stage, attempt, metrics)
        logger.info(
            "Stage %s completed successfully | audit attempt %s", stage, attempt
        )
        return metrics
    finally:
        engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("stage", choices=["extract", "transform", "validate", "load"])
    parser.add_argument("--run-id", default=os.environ.get("ETL_RUN_ID"))
    args = parser.parse_args()
    if not args.run_id:
        parser.error("Provide --run-id or ETL_RUN_ID")
    setup_logger()
    run_stage(args.stage, args.run_id, audit=True)
