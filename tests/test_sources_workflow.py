import json
import pytest
from sqlalchemy import text
from test_load_integration import engine
from src.sources_workflow import extract_source, process_sources


def inputs(tmp_path):
    path = tmp_path / "data/sources/input"
    path.mkdir(parents=True)
    (path / "himalayas.json").write_text(json.dumps({"jobs": [{"guid": "hima"}]}))
    for i in range(1, 4):
        (path / f"page-{i}.json").write_text(json.dumps({"data": [{"slug": "one"}]}))


def test_separate_extraction_and_failure_history(engine, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    inputs(tmp_path)
    extract_source(engine, "run", "himalayas", 1)
    extract_source(engine, "run", "arbeitnow", 1)
    (tmp_path / "data/sources/input/page-1.json").write_text("invalid")
    with pytest.raises(json.JSONDecodeError):
        extract_source(engine, "run", "arbeitnow", 2)
    with pytest.raises(ValueError, match="latest"):
        process_sources(engine, "run", 1)
    with engine.connect() as c:
        rows = (
            c.execute(
                text(
                    "SELECT source,status,extracted,error_type FROM source_extraction_attempts ORDER BY source,attempt"
                )
            )
            .mappings()
            .all()
        )
    assert len(rows) == 3
    assert rows[0]["extracted"] == 1 and rows[1]["status"] == "failed"
    assert rows[2]["source"] == "himalayas" and rows[2]["status"] == "success"
