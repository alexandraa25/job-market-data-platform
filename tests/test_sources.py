import json
from pathlib import Path
import pytest

from src.sources.arbeitnow import API_URL, fetch_jobs
from src.sources.adapters import (
    arbeitnow_row,
    himalayas_row,
    duplicate_candidates,
    plain_text,
)
from src.sources_pilot import pilot


def job(slug="one", title="Data Engineer"):
    return dict(
        slug=slug,
        title=title,
        company_name="Example",
        description="<p>SQL pipelines</p>",
        created_at=1760000000,
        url="https://www.arbeitnow.com/view/" + slug,
        location="Berlin",
        remote=False,
        job_types=["Full-time"],
        tags=["Data"],
    )


class Response:
    def __init__(self, data):
        self.data = data

    def raise_for_status(self):
        pass

    def json(self):
        return self.data


class Session:
    def __init__(self, pages):
        self.pages, self.calls = iter(pages), []

    def get(self, url, timeout):
        self.calls.append(url)
        assert timeout == 30
        return Response(next(self.pages))


def test_fetch_deduplicates_and_respects_page_limit():
    second = API_URL + "?page=2"
    session = Session(
        [
            dict(data=[job()], links=dict(next=second)),
            dict(data=[job(), job("two")], links=dict(next=API_URL + "?page=3")),
        ]
    )
    result = fetch_jobs(2, session)
    assert len(result["data"]) == 2
    assert result["extraction"]["duplicates_removed"] == 1
    assert result["extraction"]["truncated"] is True
    assert len(session.calls) == 2


@pytest.mark.parametrize("next_url", [API_URL, "https://external.example/api"])
def test_fetch_rejects_cycle_or_foreign_pagination(next_url):
    session = Session([dict(data=[job()], links=dict(next=next_url))])
    with pytest.raises(ValueError):
        fetch_jobs(3, session)
    assert len(session.calls) == 1


def test_adapters_preserve_source_identity_and_missing_salary():
    row = arbeitnow_row(job())
    assert row["guid"] == "arbeitnow:one" and row["source_job_id"] == "one"
    assert row["minSalary"] is None and row["maxSalary"] is None
    assert row["locationRestrictions"] == [] and row["location_text"] == "Berlin"
    assert row["categories"] == [] and row["source_tags"] == ["Data"]
    assert plain_text("<script>bad()</script><p>R&D SQL</p>") == "R&D SQL"


def test_cross_source_matches_are_candidates_only():
    first = arbeitnow_row(job())
    second = himalayas_row(
        dict(guid="hima-one", title=" data engineer ", companyName="EXAMPLE")
    )
    candidates = duplicate_candidates([first, second])
    assert len(candidates) == 1 and candidates[0]["action"] == "review_only"
    assert len(candidates[0]["guids"]) == 2


def test_pilot_retains_provenance_and_reports_invalid_dates(tmp_path):
    good = job()
    bad = {**job("invalid"), "created_at": "invalid"}
    output = tmp_path / "pilot"
    report = pilot(
        {"jobs": []},
        [{"data": [good, good, bad, job("filtered", "Accountant")]}],
        output,
    )
    assert report["arbeitnow_duplicates_removed"] == 1
    assert report["arbeitnow_filtered_out"] == 1
    assert report["quality"]["accepted"] == 1 and report["quality"]["rejected"] == 1
    accepted = json.loads((output / "accepted.json").read_text())
    assert accepted[0]["source"] == "arbeitnow" and accepted[0]["minSalary"] is None
    with pytest.raises(ValueError, match="new output"):
        pilot({"jobs": []}, [], output)


from src.sources.policy import select_job


@pytest.mark.parametrize(
    "title,status,role",
    [
        ("Senior Data Platform Engineer", "include", "Data Engineer"),
        ("Lead Analyste Data Marketing - CRM", "include", "Data Analyst"),
        ("Data Protection Engineer", "exclude", None),
        ("Data Centre Infrastructure Engineer", "exclude", None),
        ("Data & AI Pre-Sales Consultant", "exclude", None),
        ("Director, Data Science", "review", None),
        ("Oracle Data Warehouse / BI-Developer", "review", None),
        ("Senior Solutions Architect - Data & AI Engineer", "review", None),
    ],
)
def test_selection_avoids_forcing_ambiguous_roles(title, status, role):
    result = select_job(title)
    assert result["status"] == status and result["role"] == role


def test_review_is_separate_from_quality_rejection(tmp_path):
    output = tmp_path / "review-pilot"
    report = pilot(
        {"jobs": []},
        [
            {
                "data": [
                    job(),
                    job("review", "Data Architect"),
                    job("privacy", "Data Protection Manager"),
                ]
            }
        ],
        output,
    )
    assert report["candidate_decisions"] == {"include": 1, "review": 1, "exclude": 1}
    assert report["quality"]["rejected"] == 0
    assert len(json.loads((output / "review.json").read_text(encoding="utf-8"))) == 1


from src.sources.review import fingerprint


def test_snapshot_review_overrides_only_matching_content(tmp_path):
    raw = job("mixed", "Data Warehouse Developer")
    row = arbeitnow_row(raw)
    review = {
        "guid": row["guid"],
        "fingerprint": fingerprint(row),
        "status": "include",
        "role": "Data Engineer",
        "reason": "ETL ownership reviewed",
        "reviewer": "test_fixture",
    }
    report = pilot({"jobs": []}, [{"data": [raw]}], tmp_path / "reviewed", [review])
    assert report["roles_by_source"]["arbeitnow"] == {"Data Engineer": 1}
    with pytest.raises(ValueError, match="Stale review"):
        pilot(
            {"jobs": []},
            [{"data": [{**raw, "description": "changed"}]}],
            tmp_path / "stale",
            [review],
        )
    with pytest.raises(ValueError, match="Duplicate or unknown"):
        pilot({"jobs": []}, [{"data": [raw]}], tmp_path / "duplicate", [review, review])
