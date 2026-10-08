from src.ml_compare import compare
from test_ml import labelled_fixture


def test_comparison_excludes_holdout_and_predicts_every_development_row_once():
    rows = labelled_fixture()
    previous = {"test_guids": [rows[0]["guid"]], "test_text_hashes": []}
    report = compare(rows, previous, folds=3)
    validations = [
        guid for fold in report["assignments"] for guid in fold["validation_guids"]
    ]
    assert len(validations) == len(set(validations)) == len(rows) - 1
    assert rows[0]["guid"] not in validations
    for fold in report["assignments"]:
        assert not set(fold["train_guids"]) & set(fold["validation_guids"])
        assert rows[0]["guid"] not in fold["train_guids"]
    assert set(report["results"]) == {"title_only", "title_description", "rules"}
    assert len(report["results"]["title_only"]["fold_macro_f1"]) == 3
