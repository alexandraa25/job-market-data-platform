"""Real PostgreSQL tests, enabled only with TEST_DATABASE_URL."""

import logging
import os
from pathlib import Path
from uuid import uuid4

import pandas as pd
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import IntegrityError

from src.load import upsert_jobs
from src.transform import (
    transform_jobs,
    normalize_list_columns,
    add_primary_role,
    extract_skills,
)


@pytest.fixture
def engine():
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        pytest.skip("Set TEST_DATABASE_URL to a dedicated PostgreSQL test database")
    if not make_url(url).database.endswith("_test"):
        pytest.fail("Integration tests require a database name ending in _test")
    admin = create_engine(url)
    schema = "test_upsert_" + uuid4().hex
    isolated = None
    try:
        with admin.begin() as connection:
            connection.execute(text(f'CREATE SCHEMA "{schema}"'))
        isolated = create_engine(
            url, connect_args={"options": f"-csearch_path={schema}"}
        )
        # Use the real jobs schema, excluding the unrelated CREATE DATABASE statement.
        ddl = (Path(__file__).parents[1] / "sql/init.sql").read_text().split(";")[0]
        with isolated.begin() as connection:
            connection.execute(text(ddl))
            for migration in sorted(
                (Path(__file__).parents[1] / "sql/migrations").glob("*.sql")
            ):
                for statement in migration.read_text().split(";"):
                    if statement.strip():
                        connection.execute(text(statement))
        yield isolated
    finally:
        if isolated is not None:
            isolated.dispose()
        with admin.begin() as connection:
            connection.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
        admin.dispose()


@pytest.fixture
def jobs():
    job = {
        "guid": "000123",
        "search_query": "data engineer",
        "title": "Data Engineer",
        "companyName": "Test Company",
        "employmentType": "Full Time",
        "minSalary": 50000,
        "maxSalary": 70000,
        "salaryPeriod": "annual",
        "currency": "USD",
        "seniority": ["Senior"],
        "locationRestrictions": [],
        "categories": ["Data"],
        "parentCategories": [],
        "description": "Python SQL",
        "pubDate": 1760000000,
        "expiryDate": None,
        "applicationLink": "https://example.com/job",
    }
    return extract_skills(
        add_primary_role(normalize_list_columns(transform_jobs({"jobs": [job]})))
    )


def snapshot(engine):
    with engine.connect() as connection:
        return [
            dict(row)
            for row in connection.execute(
                text("SELECT * FROM jobs ORDER BY guid")
            ).mappings()
        ]


def assert_counts(caplog, inserted, updated, skipped):
    assert (
        f"Inserted: {inserted} | Updated: {updated} | Skipped: {skipped}" in caplog.text
    )


def test_new_job_insert(engine, jobs, caplog):
    caplog.set_level(logging.INFO, logger="src.load")
    upsert_jobs(jobs, engine)
    rows = snapshot(engine)
    assert len(rows) == 1
    assert rows[0]["guid"] == "000123"
    assert rows[0]["company_name"] == "Test Company"
    assert rows[0]["expiry_date"] is None
    assert rows[0]["has_python"] == 1
    assert rows[0]["created_at"] == rows[0]["updated_at"]
    assert_counts(caplog, 1, 0, 0)


def test_identical_batch_skipped(engine, jobs, caplog):
    upsert_jobs(jobs, engine)
    before = snapshot(engine)
    caplog.set_level(logging.INFO, logger="src.load")
    upsert_jobs(jobs, engine)
    assert snapshot(engine) == before
    assert_counts(caplog, 0, 0, 1)


def test_changed_field_updates_audit(engine, jobs, caplog):
    upsert_jobs(jobs, engine)
    before = snapshot(engine)[0]
    changed = jobs.copy()
    changed.loc[0, "title"] = "Senior Data Engineer"
    caplog.set_level(logging.INFO, logger="src.load")
    upsert_jobs(changed, engine)
    after = snapshot(engine)[0]
    assert after["title"] == "Senior Data Engineer"
    assert after["created_at"] == before["created_at"]
    assert after["updated_at"] > before["updated_at"]
    assert len(snapshot(engine)) == 1
    assert_counts(caplog, 0, 1, 0)


def test_batch_error_rolls_back_insert_and_update(engine, jobs, caplog):
    upsert_jobs(jobs, engine)
    before = snapshot(engine)
    changed = jobs.copy()
    changed.loc[0, "title"] = "Changed but rolled back"
    new = jobs.copy()
    new.loc[0, "guid"] = "new-job"
    invalid = jobs.copy()
    invalid.loc[0, "guid"] = None
    batch = pd.concat([changed, new, invalid], ignore_index=True)
    caplog.set_level(logging.INFO, logger="src.load")
    with pytest.raises(IntegrityError):
        upsert_jobs(batch, engine)
    assert snapshot(engine) == before
    assert "PostgreSQL UPSERT completed" not in caplog.text
