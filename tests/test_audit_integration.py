from pathlib import Path
import pytest
from sqlalchemy import text
from test_load_integration import engine
from src.audit import begin_stage, finish_stage
from src import stages


@pytest.fixture
def audit_engine(engine):
    ddl = (Path(__file__).parents[1] / "sql/migrations/001_run_audit.sql").read_text()
    with engine.begin() as connection:
        for statement in ddl.split(";"):
            if statement.strip():
                connection.execute(text(statement))
    return engine


def row(engine):
    with engine.connect() as connection:
        return dict(connection.execute(text("SELECT * FROM job_runs")).mappings().one())


def test_retry_keeps_failure_history(audit_engine):
    first = begin_stage(audit_engine, "run", "extract", "airflow")
    finish_stage(audit_engine, "run", "extract", first, error_type="TimeoutError")
    assert row(audit_engine)["status"] == "failed"
    second = begin_stage(audit_engine, "run", "extract", "airflow")
    assert second == 2
    assert row(audit_engine)["finished_at"] is None
    finish_stage(audit_engine, "run", "extract", second, {"extracted": 3})
    for stage in ("transform", "validate", "load"):
        attempt = begin_stage(audit_engine, "run", stage, "airflow")
        finish_stage(audit_engine, "run", stage, attempt,
                     {"inserted": 1, "updated": 1, "skipped": 1} if stage == "load" else {})
    result = row(audit_engine)
    assert result["status"] == "success"
    assert result["error_type"] is None
    assert result["extracted"] == 3
    assert result["finished_at"] > result["started_at"]
    with audit_engine.connect() as connection:
        assert connection.execute(text("SELECT count(*) FROM job_run_attempts WHERE status='failed'")).scalar_one() == 1


def test_wrapper_records_real_failure_without_message(audit_engine, monkeypatch):
    monkeypatch.setattr(stages, "create_db_engine", lambda: audit_engine)
    def fail(*args):
        raise ValueError("password=do-not-persist")
    monkeypatch.setattr(stages, "_execute_stage", fail)
    with pytest.raises(ValueError):
        stages.run_stage("extract", "failed-run", audit=True)
    result = row(audit_engine)
    assert result["status"] == "failed"
    assert result["error_type"] == "ValueError"
    assert "do-not-persist" not in str(result)


def test_rerun_resets_old_summary(audit_engine):
    attempt = begin_stage(audit_engine, "run", "load", "manual")
    finish_stage(audit_engine, "run", "load", attempt, {"inserted": 3})
    begin_stage(audit_engine, "run", "extract", "manual")
    result = row(audit_engine)
    assert result["status"] == "running"
    assert result["inserted"] is None
