from src.ml_final_batch import reserve, blind_page


def test_reservation_excludes_old_guid_text_and_title_without_suggestions():
    old = {"guid": "old", "title": "Old title", "description": "Old body"}
    rows = [
        old,
        {**old, "guid": "copy"},
        {"guid": "same-title", "title": "OLD TITLE", "description": "New body"},
        {"guid": "new", "title": "New title", "description": "New description"},
    ]
    queue, available = reserve(rows, [old])
    assert available == 1 and queue[0]["guid"] == "new"
    assert "rule_role" not in queue[0] and not queue[0]["reviewed"]
    template = '<details><summary>Clasificarea regulilor existente (optional)</summary><p id="suggestion"></p></details><script type="application/json">[]</script>'
    assert "suggestion" not in blind_page(template, queue)
    assert '"guid": "new"' in blind_page(template, queue)
