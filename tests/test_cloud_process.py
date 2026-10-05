import hashlib, json
from pathlib import Path
import pytest

pytest.importorskip("pyspark")
from test_spark_process import spark
from src.cloud_process import process_cloud
from src.spark_process import transform, partition


def test_cloud_entrypoint_reuses_transform_and_verifies_parquet(spark, tmp_path):
    run = "cloud-test"
    raw = tmp_path / "raw"
    processed = tmp_path / "processed"
    directory = raw / "jobs" / hashlib.sha256(run.encode()).hexdigest()
    directory.mkdir(parents=True)
    base = {
        "guid": "a",
        "title": " Data Engineer SQL ",
        "companyName": " Example ",
        "pubDate": 1700000000,
        "minSalary": 100,
        "maxSalary": 200,
        "description": "Python Azure",
        "categories": [],
        "parentCategories": [],
        "seniority": ["Senior"],
        "locationRestrictions": ["Europe"],
    }
    jobs = [base, dict(base), {**base, "guid": "b", "minSalary": "bad"}]
    (directory / "raw.json").write_text(json.dumps({"jobs": jobs}))
    report = process_cloud(
        spark,
        run,
        str(raw),
        str(processed),
        lambda path, content: Path(path).write_text(content),
    )
    assert (
        report["input"],
        report["deduplicated"],
        report["accepted"],
        report["rejected"],
    ) == (3, 2, 1, 1)
    manifest = json.loads(Path(report["manifest_path"]).read_text())
    assert manifest == report
    good, _ = partition(transform(spark, jobs))
    actual = spark.read.parquet(report["accepted_path"])
    assert good.exceptAll(actual).count() == 0 and actual.exceptAll(good).count() == 0
    assert (
        "invalid_minSalary"
        in spark.read.parquet(report["rejected_path"]).first().rejection_reasons
    )


def test_empty_cloud_batch_never_publishes_manifest(spark, tmp_path):
    run = "empty-cloud"
    directory = tmp_path / "raw" / "jobs" / hashlib.sha256(run.encode()).hexdigest()
    directory.mkdir(parents=True)
    (directory / "raw.json").write_text('{"jobs": []}')
    calls = []
    with pytest.raises(ValueError, match="No accepted rows"):
        process_cloud(
            spark,
            run,
            str(tmp_path / "raw"),
            str(tmp_path / "processed"),
            lambda *args: calls.append(args),
        )
    assert calls == []
