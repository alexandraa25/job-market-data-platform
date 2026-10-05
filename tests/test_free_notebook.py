import ast, json
from pathlib import Path
import pytest

pytest.importorskip("pyspark")
from test_spark_process import spark


@pytest.fixture
def notebook_code():
    path = Path(__file__).parents[1] / "databricks/Job_Market_PySpark_FreeEdition.py"
    tree = ast.parse(path.read_text(encoding="utf-8-sig"))
    nodes = [
        n
        for n in tree.body
        if isinstance(n, (ast.Import, ast.ImportFrom, ast.FunctionDef))
        or (
            isinstance(n, ast.Assign)
            and getattr(n.targets[0], "id", "") in ("STRING_COLUMNS", "LIST_COLUMNS")
        )
    ]
    namespace = {}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(path), "exec"), namespace)
    return namespace["process_snapshot"]


def base():
    return {
        "guid": "a",
        "title": " Data Engineer Python SQL ",
        "companyName": " Example ",
        "pubDate": 1700000000,
        "expiryDate": None,
        "minSalary": 100,
        "maxSalary": 200,
        "description": "Azure",
        "categories": [],
        "parentCategories": [],
        "seniority": ["Senior"],
        "locationRestrictions": ["Europe"],
    }


def test_complete_free_notebook(spark, tmp_path, notebook_code):
    b = base()
    jobs = [
        b,
        {**b, "title": "Different duplicate"},
        {**b, "guid": "b", "minSalary": "broken"},
        {**b, "guid": "c", "minSalary": None, "maxSalary": None},
        {**b, "guid": "d", "pubDate": "broken"},
        {**b, "guid": "e", "minSalary": 300},
        {**b, "guid": "f", "expiryDate": "broken"},
        {**b, "guid": "g", "minSalary": -1},
        {**b, "guid": "h", "maxSalary": "Infinity"},
    ]
    raw = tmp_path / "raw.json"
    raw.write_text(json.dumps({"jobs": jobs}))
    report = notebook_code(
        spark, str(raw), str(tmp_path / "out"), lambda p, c: Path(p).write_text(c)
    )
    assert report["input"] == 9 and report["duplicates_removed"] == 1
    assert report["accepted"] == 2 and report["rejected"] == 6
    assert report["reason_counts"]["invalid_minSalary"] == 2
    good = spark.read.parquet(report["accepted_path"])
    a = good.filter("guid='a'").first()
    assert (
        a.title == "Data Engineer Python SQL" and a.has_python == 1 and a.has_sql == 1
    )
    assert json.loads(Path(report["manifest_path"]).read_text())["status"] == "success"
    assert Path(report["quality_report_path"]).exists()


def test_blocked_batch_retains_diagnostics_without_manifest(
    spark, tmp_path, notebook_code
):
    raw = tmp_path / "raw.json"
    raw.write_text(
        json.dumps({"jobs": [{**base(), "guid": "a", "minSalary": "broken"}]})
    )
    with pytest.raises(ValueError, match="No accepted rows"):
        notebook_code(
            spark, str(raw), str(tmp_path / "out"), lambda p, c: Path(p).write_text(c)
        )
    assert len(list((tmp_path / "out").rglob("quality_report.json"))) == 1
    assert not list((tmp_path / "out").rglob("manifest.json"))
    report = json.loads(
        next((tmp_path / "out").rglob("quality_report.json")).read_text()
    )
    assert report["status"] == "blocked_no_accepted_rows" and report["rejected"] == 1
