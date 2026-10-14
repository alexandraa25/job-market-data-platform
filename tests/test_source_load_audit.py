import json
import pytest
import pandas as pd
from sqlalchemy import text
from test_load_integration import engine, jobs
from src.sources_load import load_snapshot


def save(tmp_path, jobs):
    first = jobs.copy()
    first["source"] = "himalayas"
    first["source_job_id"] = first.guid
    first["source_url"] = first.applicationLink
    second = first.copy()
    second["guid"] = "arbeitnow:one"
    second["source"] = "arbeitnow"
    second["source_job_id"] = "one"
    path = tmp_path / "accepted.json"
    pd.concat([first, second]).to_json(path, orient="records", date_format="iso")
    return path


def test_audit_source_counts_and_repeat(engine, jobs, tmp_path):
    path = save(tmp_path, jobs)
    first = load_snapshot(path, engine)
    second = load_snapshot(path, engine)
    assert first["load"]["inserted"] == 2
    assert second["load"] == {"inserted": 0, "updated": 0, "skipped": 2}
    with engine.connect() as connection:
        rows = (
            connection.execute(
                text("SELECT * FROM source_load_runs WHERE run_id=:run"),
                {"run": second["run_id"]},
            )
            .mappings()
            .all()
        )
    assert len(rows) == 2
    assert all(
        r["status"] == "success" and r["skipped"] == 1 and r["input_rows"] == 1
        for r in rows
    )


def test_load_failure_rolls_back_and_keeps_source_audit(
    engine, jobs, tmp_path, monkeypatch
):
    path = save(tmp_path, jobs)
    from src import load

    def fail(connection, records):
        raise RuntimeError("secret-do-not-store")

    monkeypatch.setattr(load, "sync_dimensions", fail)
    with pytest.raises(RuntimeError):
        load_snapshot(path, engine)
    with engine.connect() as connection:
        assert connection.execute(text("SELECT count(*) FROM jobs")).scalar_one() == 0
        rows = (
            connection.execute(text("SELECT * FROM source_load_runs")).mappings().all()
        )
    assert len(rows) == 2 and all(
        r["status"] == "failed" and r["inserted"] == 0 for r in rows
    )
    assert all(r["error_type"] == "RuntimeError" for r in rows)
    assert "secret-do-not-store" not in str(rows)
