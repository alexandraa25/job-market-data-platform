from src.ml_review_round import select_round


def test_round_excludes_previous_guid_and_text_and_resets_labels():
    rows = [
        dict(
            guid=str(i),
            title=f"Unique vacancy {i}",
            description="",
            rule_role="Other",
            reviewed=True,
            human_label="Other",
            label_source="human",
            reviewed_at="old",
        )
        for i in range(5)
    ]
    duplicate = {**rows[0], "guid": "different-guid"}
    queue = select_round(rows + [duplicate], [rows[0]], other_count=10)
    assert {row["guid"] for row in queue} == {"1", "2", "3", "4"}
    assert all(
        not row["reviewed"]
        and row["human_label"] == ""
        and row["label_source"] == ""
        and "reviewed_at" not in row
        for row in queue
    )
    assert queue == select_round(
        list(reversed(rows)) + [duplicate], [rows[0]], other_count=10
    )
