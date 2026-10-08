from src.ml import text_hash
from src.ml_iteration import development_rows
from test_ml import labelled_fixture


def test_previous_holdout_excludes_guid_and_same_text():
    rows = labelled_fixture()
    previous = {
        "test_guids": [rows[0]["guid"]],
        "test_text_hashes": [text_hash(rows[1])],
    }
    result = development_rows(rows, previous)
    assert len(result) == len(rows) - 2
    assert rows[0] not in result and rows[1] not in result
