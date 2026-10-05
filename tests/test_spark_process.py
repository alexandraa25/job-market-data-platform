import json
from pathlib import Path
import pandas as pd
import pytest

pytest.importorskip("pyspark")
from pyspark.sql import SparkSession
from src.spark_process import transform, partition
from src.transform import (
    transform_jobs,
    normalize_list_columns,
    add_primary_role,
    extract_skills,
)
from src.quality import assess_jobs


@pytest.fixture(scope="module")
def spark():
    session = (
        SparkSession.builder.master("local[2]")
        .config("spark.sql.session.timeZone", "UTC")
        .config("spark.sql.shuffle.partitions", "2")
        .config("spark.ui.enabled", "false")
        .getOrCreate()
    )
    session.sparkContext.setLogLevel("ERROR")
    yield session
    session.stop()


def test_transform_quality_and_parquet(spark, tmp_path):
    base = {
        "guid": "a",
        "title": "  Data Engineer Python SQL  ",
        "companyName": " Example ",
        "pubDate": 1700000000,
        "expiryDate": None,
        "minSalary": 100,
        "maxSalary": 200,
        "description": "Azure PySpark",
        "seniority": ["Senior"],
        "locationRestrictions": ["Europe"],
        "categories": [],
        "parentCategories": [],
        "search_query": "data engineer",
        "employmentType": "Full Time",
        "salaryPeriod": "year",
        "currency": "USD",
        "applicationLink": "https://example.org",
    }
    jobs = [
        base,
        dict(base),
        {**base, "guid": "b", "minSalary": "bad"},
        {**base, "guid": "c", "minSalary": 300},
        {**base, "guid": "d", "pubDate": "bad"},
        {**base, "guid": "e", "minSalary": None, "maxSalary": 200},
        {**base, "guid": "f", "title": "ML Engineer"},
    ]
    df = transform(spark, jobs)
    good, bad = partition(df)
    assert df.count() == 6
    assert {r.guid for r in good.collect()} == {"a", "e", "f"}
    assert {r.guid for r in bad.collect()} == {"b", "c", "d"}
    a = good.filter("guid='a'").first()
    assert (
        a.avgSalary == 150
        and a.primary_role == "Data Engineer"
        and a.has_python == 1
        and a.has_pyspark == 1
    )
    good.write.parquet(str(tmp_path / "good"))
    assert spark.read.parquet(str(tmp_path / "good")).count() == 3


def test_live_snapshot_matches_pandas(spark):
    path = Path(
        "data/runs/13fada25cf34bf7555e69de557c1eac4581f03f50a61708f5013b9634b516c9d/raw.json"
    )
    if not path.exists():
        pytest.skip("Local demonstration snapshot unavailable")
    data = json.loads(path.read_text())
    expected = extract_skills(
        add_primary_role(normalize_list_columns(transform_jobs(data)))
    )
    expected_good, expected_bad, _ = assess_jobs(expected)
    good, bad = partition(transform(spark, data["jobs"]))
    assert good.count() == len(expected_good) and bad.count() == len(expected_bad)
    actual = (
        pd.DataFrame([r.asDict() for r in good.collect()])
        .set_index("guid")
        .sort_index()
    )
    expected_good = expected_good.set_index("guid").sort_index()
    for col in expected_good.columns:
        left = actual[col]
        right = expected_good[col]
        if col in ("pubDate", "expiryDate"):
            left = pd.to_datetime(left)
            right = pd.to_datetime(right)
        pd.testing.assert_series_equal(
            left, right, check_dtype=False, check_names=False, check_exact=False
        )
