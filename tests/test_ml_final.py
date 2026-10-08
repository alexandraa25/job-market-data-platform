import pytest
from src.ml_final import validate_final


def test_final_requires_unchanged_reserved_data_and_rejects_leakage():
    reserved = [dict(guid="new", title="New vacancy", description="Responsibilities")]
    labelled = [
        {
            **reserved[0],
            "human_label": "Other",
            "label_source": "human",
            "reviewed": True,
        }
    ]
    assert validate_final(labelled, reserved, []) == labelled
    with pytest.raises(ValueError, match="changed"):
        validate_final([{**labelled[0], "title": "Edited"}], reserved, [])
    with pytest.raises(ValueError, match="overlaps"):
        validate_final(labelled, reserved, [{**reserved[0], "guid": "different"}])
    with pytest.raises(ValueError, match="every reserved"):
        validate_final([], reserved, [])


def test_title_only_artifact_uses_title_for_inference(tmp_path, monkeypatch):
    import joblib
    import numpy as np
    from src.ml import predict_rows, read_rows

    class Model:
        classes_ = np.array(["Other"])

        def predict_proba(self, texts):
            assert texts == ["New vacancy"]
            return np.array([[1.0]])

    monkeypatch.setattr(
        joblib,
        "load",
        lambda path: dict(
            model=Model(), model_version="candidate", feature_mode="title_only"
        ),
    )
    output = tmp_path / "predictions.jsonl"
    assert (
        predict_rows(
            [
                dict(
                    guid="new",
                    title="<b>New vacancy</b>",
                    description="Must not enter title-only inference",
                )
            ],
            "trusted",
            output,
        )
        == 1
    )
    assert read_rows(output)[0]["ml_role"] == "Other"
