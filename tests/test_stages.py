import pandas as pd
import pytest
from src import stages


def test_typed_artifact_roundtrip(tmp_path):
    frame = pd.DataFrame(
        {
            "guid": ["000123"],
            "currency": [None],
            "pubDate": [pd.Timestamp("2026-10-03")],
            "minSalary": [float("nan")],
            "has_python": [1],
        }
    )
    frame["pubDate"] = frame["pubDate"].astype("datetime64[ns]")
    path = tmp_path / "frame.json"
    stages.write_frame(frame, path)
    restored = pd.read_json(path, orient="table")
    pd.testing.assert_frame_equal(
        frame.drop(columns="currency"), restored.drop(columns="currency")
    )
    assert pd.isna(restored.loc[0, "currency"])


def test_validation_blocks_load_and_removes_old_approval(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    directory = stages.run_directory("test")
    directory.mkdir(parents=True)
    frame = pd.DataFrame(
        {
            "guid": ["duplicate", "duplicate"],
            "title": ["Job", "Job"],
            "companyName": ["Company", "Company"],
            "avgSalary": [None, None],
        }
    )
    stages.write_frame(frame, directory / "transformed.json")
    stages.write_frame(frame, directory / "validated.json")
    with pytest.raises(ValueError, match="Validation failed"):
        stages.run_stage("validate", "test")
    assert not (directory / "validated.json").exists()
    with pytest.raises(FileNotFoundError):
        stages.run_stage("load", "test")


def test_runs_are_isolated():
    assert stages.run_directory("../run") != stages.run_directory("run")
    assert stages.run_directory("../run").parent == stages.Path("data/runs")
