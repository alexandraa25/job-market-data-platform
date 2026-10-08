from src.ml_demo import render


def test_demo_escapes_job_text_and_discloses_experimental_status():
    page = render(
        [dict(title="<script>bad()</script>")],
        [dict(rule_role="Other", ml_role="Other", ml_score=0.4, needs_review=True)],
        "local",
    )
    assert "<script>" not in page and "&lt;script&gt;" in page
    assert "Revizuire" in page and "ML experimental" in page
    assert "probabilitate calibrata" in page
