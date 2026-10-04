import json
import pandas as pd
import pytest
from src.quality import assess_jobs, validate_and_save


def valid_frame():
    return pd.DataFrame({"guid": ["ok"], "title": ["Data Engineer"], "companyName": ["Company"],
                         "minSalary": [10.0], "maxSalary": [20.0], "avgSalary": [15.0],
                         "pubDate": [pd.Timestamp("2026-10-01")],
                         "expiryDate": [pd.Timestamp("2026-11-01")],
                         "primary_role": ["Data Engineer"], "has_python": [1]})


@pytest.mark.parametrize("column,value,reason", [
    ("guid", " ", "missing_guid"), ("title", None, "missing_title"),
    ("companyName", "", "missing_companyName"), ("minSalary", -1, "invalid_minSalary"),
    ("minSalary", 30, "salary_range_reversed"), ("pubDate", pd.NaT, "missing_or_invalid_pubDate"),
    ("expiryDate", pd.Timestamp("2026-09-01"), "expiry_before_publication"),
    ("has_python", 2, "invalid_has_python"), ("primary_role", "Unknown", "invalid_primary_role"),
])
def test_reasons(column, value, reason):
    frame = valid_frame()
    frame[column] = value
    accepted, rejected, report = assess_jobs(frame)
    assert accepted.empty
    assert reason in rejected.iloc[0].rejection_reasons
    assert report["reason_counts"][reason] == 1


def test_partial_batch_and_missing_optional_values(tmp_path):
    good = valid_frame()
    good[["minSalary", "maxSalary", "avgSalary"]] = float("nan")
    good["expiryDate"] = pd.NaT
    bad = valid_frame()
    bad["guid"] = "bad"
    bad["title"] = ""
    accepted = validate_and_save(pd.concat([good, bad]), tmp_path)
    assert accepted.guid.tolist() == ["ok"]
    assert pd.read_csv(tmp_path / "rejected.csv").guid.tolist() == ["bad"]
    report = json.loads((tmp_path / "quality_report.json").read_text())
    assert (report["accepted"], report["rejected"]) == (1, 1)


def test_all_duplicates_rejected_and_report_saved(tmp_path):
    with pytest.raises(ValueError, match="no accepted rows"):
        validate_and_save(pd.concat([valid_frame(), valid_frame()]), tmp_path)
    assert len(pd.read_csv(tmp_path / "rejected.csv")) == 2


def test_coercion_marker_rejects_and_is_not_loaded():
    frame = valid_frame()
    frame["_dq_invalid_expiryDate"] = True
    accepted, rejected, _ = assess_jobs(frame)
    assert accepted.empty
    assert "invalid_expiryDate" in rejected.iloc[0].rejection_reasons
    assert "_dq_invalid_expiryDate" not in rejected
