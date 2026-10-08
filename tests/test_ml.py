import json
import pytest

from src.ml import (
    ROLES,
    clean_text,
    prepare,
    reviewed_rows,
    text_hash,
    train_model,
    predict_rows,
)


def labelled_fixture():
    terms = {
        "Data Engineer": "pipeline warehouse airflow",
        "Data Analyst": "dashboard reporting analysis",
        "Data Scientist": "statistics experiments research",
        "Machine Learning Engineer": "inference deployment algorithms",
        "Other": "customer sales accounting",
    }
    return [
        {
            "guid": f"{i}-{j}",
            "title": f"{role} vacancy {j}",
            "description": f"{terms[role]} distinctive detail {j}",
            "human_label": role,
            "reviewed": True,
            "label_source": "human",
        }
        for i, role in enumerate(ROLES)
        for j in range(12)
    ]


def test_prepare_deduplicates_and_never_fabricates_labels(tmp_path):
    rows = [
        {
            "guid": "a",
            "title": "Data Engineer",
            "description": "<p>SQL</p><script>ignore</script>",
        },
        {"guid": "b", "title": "Data Engineer", "description": "SQL"},
    ]
    report = prepare(rows, tmp_path / "prepared")
    assert report["unique_texts"] == 1
    assert report["duplicates_removed"] == 1
    queue = [
        json.loads(line)
        for line in (tmp_path / "prepared/review_queue.jsonl").read_text().splitlines()
    ]
    assert all(row["reviewed"] is False and row["human_label"] == "" for row in queue)
    assert clean_text(rows[0]["description"]) == "SQL"
    with pytest.raises(FileExistsError):
        prepare(rows, tmp_path / "prepared")


def test_training_refuses_automatic_or_insufficient_labels():
    rows = labelled_fixture()
    with pytest.raises(ValueError, match="human label"):
        reviewed_rows([{**rows[0], "label_source": "rules"}])
    with pytest.raises(ValueError, match="independently reviewed"):
        reviewed_rows([{**row, "reviewed": False} for row in rows])


def test_training_rejects_conflicting_duplicates():
    rows = labelled_fixture()
    duplicate = {**rows[0], "guid": "duplicate", "human_label": "Other"}
    with pytest.raises(ValueError, match="Conflicting"):
        reviewed_rows(rows + [duplicate])


def test_model_holdout_no_leakage_and_prediction_roundtrip(tmp_path):
    rows = labelled_fixture()
    duplicate = {**rows[0], "guid": "duplicate"}
    output, report = train_model(rows + [duplicate], tmp_path / "models")
    assert report["reviewed_rows"] == len(rows)
    assert not set(report["train_guids"]) & set(report["test_guids"])
    assert not set(report["train_text_hashes"]) & set(report["test_text_hashes"])
    assert report["status"] == "experimental"
    assert set(report["model_report"]) >= set(ROLES)
    assert set(report["rules_report"]) >= set(ROLES)
    path = tmp_path / "predictions.jsonl"
    assert predict_rows(rows[:3], output / "model.joblib", path) == 3
    predictions = [json.loads(line) for line in path.read_text().splitlines()]
    assert all(
        row["ml_role"] in ROLES and 0 <= row["ml_score"] <= 1 for row in predictions
    )
    assert all(row["model_version"] == report["model_version"] for row in predictions)
    assert (output / "manifest.json").is_file()


def test_invalid_split_and_threshold(tmp_path):
    from src.ml import split_rows

    with pytest.raises(ValueError, match="test_size"):
        split_rows(labelled_fixture(), test_size=0.9)
    with pytest.raises(ValueError, match="threshold"):
        predict_rows([], tmp_path / "missing", tmp_path / "out", threshold=1.1)


def test_plain_text_with_unescaped_ampersand_is_preserved():
    assert (
        clean_text("Software Development Engineer _R&D")
        == "Software Development Engineer _R&D"
    )
