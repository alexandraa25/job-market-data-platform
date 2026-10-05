# Databricks notebook source
# MAGIC %md
# MAGIC # Job Market — procesare completă în Free Edition
# MAGIC Snapshot manual → transformare → validare → Parquet → raport → manifest.
# MAGIC Notebook independent. Folosește Spark Serverless și volume managed, fără secrete Azure.

# COMMAND ----------
import json
import uuid
from datetime import datetime, timezone

STRING_COLUMNS = [
    "guid",
    "search_query",
    "title",
    "companyName",
    "employmentType",
    "minSalary",
    "maxSalary",
    "salaryPeriod",
    "currency",
    "description",
    "pubDate",
    "expiryDate",
    "applicationLink",
]

LIST_COLUMNS = ["seniority", "locationRestrictions", "categories", "parentCategories"]


def raw_schema():
    from pyspark.sql import types as T

    return T.StructType(
        [T.StructField(c, T.StringType()) for c in STRING_COLUMNS]
        + [T.StructField(c, T.ArrayType(T.StringType())) for c in LIST_COLUMNS]
    )


def transform_frame(df):
    """Shared expressions for local records and a cloud-read raw DataFrame."""
    from pyspark.sql import functions as F, Window

    lists = LIST_COLUMNS
    df = (
        df.withColumn(
            "_rank",
            F.row_number().over(Window.partitionBy("guid").orderBy("_position")),
        )
        .filter("_rank = 1")
        .drop("_rank", "_position")
    )
    for c in ["title", "companyName"]:
        df = df.withColumn(c, F.trim(F.coalesce(F.col(c), F.lit(""))))
    for c in lists:
        df = df.withColumn(c, F.when(F.col(c).isNotNull(), F.concat_ws(", ", F.col(c))))
    for c in ["minSalary", "maxSalary"]:
        numeric = F.expr(f"try_cast(`{c}` as double)")
        df = df.withColumn(
            "_dq_invalid_" + c, F.col(c).isNotNull() & numeric.isNull()
        ).withColumn(c, numeric)
    for c in ["pubDate", "expiryDate"]:
        # Match pandas nanosecond timestamp range and preserve invalid input flags.
        num = F.expr(f"try_cast(`{c}` as double)")
        timestamp = F.when(
            num.between(-9223372036, 9223372036), F.timestamp_seconds(num)
        )
        df = df.withColumn(
            "_dq_invalid_" + c, F.col(c).isNotNull() & timestamp.isNull()
        ).withColumn(c, timestamp)
    df = df.withColumn(
        "avgSalary",
        F.when(F.col("minSalary").isNull(), F.col("maxSalary"))
        .when(F.col("maxSalary").isNull(), F.col("minSalary"))
        .otherwise((F.col("minSalary") + F.col("maxSalary")) / 2),
    )
    title = F.lower(F.col("title"))
    df = df.withColumn(
        "primary_role",
        F.when(
            title.contains("machine learning") | title.contains("ml engineer"),
            "Machine Learning Engineer",
        )
        .when(title.contains("data scientist"), "Data Scientist")
        .when(
            title.contains("data engineer") | title.contains("analytics engineer"),
            "Data Engineer",
        )
        .when(
            title.contains("data analyst") | title.contains("business intelligence"),
            "Data Analyst",
        )
        .otherwise("Other"),
    )
    text = F.lower(F.concat_ws(" ", F.col("title"), F.col("description")))
    for skill in [
        "python",
        "sql",
        "azure",
        "aws",
        "gcp",
        "spark",
        "pyspark",
        "databricks",
        "snowflake",
        "airflow",
        "docker",
        "kubernetes",
        "power_bi",
        "tableau",
        "tensorflow",
        "pytorch",
        "scikit_learn",
    ]:
        pattern = {
            "power_bi": r"\bpower bi\b",
            "scikit_learn": r"\bscikit[- ]learn\b",
        }.get(skill, rf"\b{skill}\b")
        df = df.withColumn("has_" + skill, text.rlike(pattern).cast("int"))
    return df


def partition(df):
    from pyspark.sql import functions as F

    rules = [
        (F.col(c).isNull() | (F.trim(F.col(c)) == ""), "missing_" + c)
        for c in ["guid", "title", "companyName"]
    ]
    rules.append((F.col("pubDate").isNull(), "missing_or_invalid_pubDate"))
    for c in ["minSalary", "maxSalary", "avgSalary"]:
        rules.append(
            (
                F.col(c).isNotNull()
                & ((F.col(c) < 0) | F.isnan(c) | (F.abs(F.col(c)) == float("inf"))),
                "invalid_" + c,
            )
        )
    rules.extend(
        [
            (F.col("minSalary") > F.col("maxSalary"), "salary_range_reversed"),
            (F.col("expiryDate") < F.col("pubDate"), "expiry_before_publication"),
        ]
    )
    for c in df.columns:
        if c.startswith("_dq_invalid_"):
            rules.append((F.col(c), c.removeprefix("_dq_")))
    df = df.withColumn(
        "rejection_reasons",
        F.concat_ws(
            " | ",
            *[
                F.when(F.coalesce(condition, F.lit(False)), F.lit(reason))
                for condition, reason in rules
            ],
        ),
    ).drop(*[c for c in df.columns if c.startswith("_dq_")])
    return df.filter("rejection_reasons = ''").drop("rejection_reasons"), df.filter(
        "rejection_reasons <> ''"
    )


# COMMAND ----------
def process_snapshot(spark, raw_path, processed_root, write_json):
    from pyspark.sql import functions as F, types as T

    schema = T.StructType([T.StructField("jobs", T.ArrayType(raw_schema()))])
    raw = (
        spark.read.schema(schema)
        .option("multiLine", True)
        .option("mode", "FAILFAST")
        .json(raw_path)
    )
    # One uploaded snapshot; array position makes duplicate selection repeatable.
    if raw.count() != 1:
        raise ValueError("Expected one JSON snapshot object")
    rows = raw.select(F.posexplode("jobs").alias("_position", "job")).select(
        "_position", "job.*"
    )
    frame = transform_frame(rows)
    accepted, rejected = partition(frame)
    total = frame.count()
    processing_id = uuid.uuid4().hex
    prefix = f'{processed_root.rstrip("/")}/job_market/{processing_id}'
    reasons = (
        rejected.select(
            F.explode(F.split("rejection_reasons", r" \| ")).alias("reason")
        )
        .groupBy("reason")
        .count()
    )
    report = {
        "processing_id": processing_id,
        "processed_at_utc": datetime.now(timezone.utc).isoformat(),
        "raw_path": raw_path,
        "input": rows.count(),
        "deduplicated": total,
        "duplicates_removed": rows.count() - total,
        "accepted": accepted.count(),
        "rejected": rejected.count(),
        "reason_counts": {r.reason: r["count"] for r in reasons.collect()},
    }
    report["rejected_percent"] = (
        round(100 * report["rejected"] / total, 2) if total else 0
    )
    report["quality_report_path"] = prefix + "/quality_report.json"
    report["rejected_path"] = prefix + "/rejected"
    report["accepted_path"] = prefix + "/accepted"
    # Retain diagnostics even when no accepted rows remain. No completion manifest.
    rejected.write.mode("overwrite").parquet(report["rejected_path"])
    report["status"] = "validated" if report["accepted"] else "blocked_no_accepted_rows"
    write_json(report["quality_report_path"], json.dumps(report, indent=2))
    if not report["accepted"]:
        raise ValueError(
            "No accepted rows; see quality_report.json and rejected Parquet"
        )
    accepted.write.mode("overwrite").parquet(report["accepted_path"])
    for name, expected in [("accepted", accepted), ("rejected", rejected)]:
        actual = spark.read.parquet(report[name + "_path"])
        if (
            actual.count() != report[name]
            or expected.exceptAll(actual).limit(1).count()
            or actual.exceptAll(expected).limit(1).count()
        ):
            raise ValueError("Parquet content verification failed: " + name)
    report["status"] = "success"
    report["verification"] = "row_count_and_row_content"
    report["manifest_path"] = prefix + "/manifest.json"
    write_json(report["manifest_path"], json.dumps(report, indent=2))
    return report


# COMMAND ----------
dbutils.widgets.text("raw_path", "/Volumes/workspace/default/raw/raw.json")
dbutils.widgets.text("processed_root", "/Volumes/workspace/default/processed")
raw_path = dbutils.widgets.get("raw_path")
processed_root = dbutils.widgets.get("processed_root")
if not raw_path.startswith("/Volumes/") or not processed_root.startswith("/Volumes/"):
    raise ValueError("Folosește căi Unity Catalog /Volumes/...")
spark.conf.set("spark.sql.session.timeZone", "UTC")

# COMMAND ----------
result = process_snapshot(
    spark,
    raw_path,
    processed_root,
    lambda path, content: dbutils.fs.put(path, content, overwrite=False),
)
print(f"Acceptate: {result['accepted']} | Respinse: {result['rejected']}")
print(f"Parquet verificat: {result['accepted']} rânduri")
print(f"Manifest: {result['manifest_path']}")
display(
    spark.read.parquet(result["accepted_path"]).select(
        "title", "companyName", "primary_role", "has_python", "has_sql"
    )
)
display(spark.read.parquet(result["rejected_path"]))

# COMMAND ----------
dbutils.notebook.exit(json.dumps(result))
