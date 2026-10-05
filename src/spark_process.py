"""Standalone local Spark processing of an Azure raw snapshot."""

import argparse
import hashlib
import json
import logging
import os
import uuid
from pathlib import Path
from contextlib import contextmanager


@contextmanager
def lake():
    from azure.identity import ClientSecretCredential
    from azure.storage.filedatalake import DataLakeServiceClient

    names = (
        "AZURE_STORAGE_ACCOUNT_NAME",
        "AZURE_TENANT_ID",
        "AZURE_CLIENT_ID",
        "AZURE_CLIENT_SECRET",
    )
    missing = [n for n in names if not os.getenv(n)]
    if missing:
        raise ValueError("Missing Azure configuration: " + ", ".join(missing))
    logging.getLogger("azure").setLevel(logging.WARNING)
    with ClientSecretCredential(
        os.environ[names[1]], os.environ[names[2]], os.environ[names[3]]
    ) as credential:
        with DataLakeServiceClient(
            account_url=f"https://{os.environ[names[0]]}.dfs.core.windows.net",
            credential=credential,
            retry_total=2,
            connection_timeout=15,
            read_timeout=60,
        ) as service:
            yield service


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


def transform(spark, jobs):
    from pyspark.sql import types as T

    strings = STRING_COLUMNS
    lists = LIST_COLUMNS
    schema = raw_schema().add("_position", T.LongType())
    rows = []
    for i, job in enumerate(jobs):
        row = {c: str(job[c]) if job.get(c) is not None else None for c in strings}
        row.update(
            {
                c: (
                    job.get(c)
                    if isinstance(job.get(c), list)
                    else ([str(job[c])] if job.get(c) is not None else None)
                )
                for c in lists
            }
        )
        row["_position"] = i
        rows.append(row)
    return transform_frame(spark.createDataFrame(rows, schema))


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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    parser.add_argument(
        "--airflow",
        action="store_true",
        help="Use local raw when Azure upload is disabled",
    )
    parser.add_argument(
        "--local-raw", type=Path, help="Offline test input; never publishes to Azure"
    )
    parser.add_argument(
        "--local-only",
        action="store_true",
        help="Read Azure but retain outputs locally",
    )
    args = parser.parse_args()
    run_hash = hashlib.sha256(args.run_id.encode()).hexdigest()
    if args.airflow:
        enabled = os.getenv("AZURE_UPLOAD_ENABLED", "false").lower()
        if enabled not in ("true", "false"):
            raise ValueError("AZURE_UPLOAD_ENABLED must be true or false")
        if enabled == "false":
            args.local_raw = Path("data/runs") / run_hash / "raw.json"
    directory = Path("data/spark") / run_hash
    directory.mkdir(parents=True, exist_ok=True)
    raw_path = f"jobs/{run_hash}/raw.json"
    if args.local_raw:
        payload = args.local_raw.read_bytes()
    else:
        try:
            with lake() as service:
                payload = (
                    service.get_file_client(
                        os.getenv("AZURE_STORAGE_CONTAINER", "raw"), raw_path
                    )
                    .download_file()
                    .readall()
                )
        except Exception as error:
            raise RuntimeError(
                "Azure raw download failed: " + type(error).__name__
            ) from None
    (directory / "raw.json").write_bytes(payload)
    jobs = json.loads(payload)["jobs"]
    from pyspark.sql import SparkSession

    spark = (
        SparkSession.builder.master("local[2]")
        .appName("job-market-processed")
        .config("spark.sql.session.timeZone", "UTC")
        .config("spark.sql.shuffle.partitions", "2")
        .config("spark.ui.enabled", "false")
        .getOrCreate()
    )
    spark.sparkContext.setLogLevel("ERROR")
    try:
        df = transform(spark, jobs).cache()
        accepted, rejected = partition(df)
        report = {
            "input": len(jobs),
            "deduplicated": df.count(),
            "accepted": accepted.count(),
            "rejected": rejected.count(),
            "raw_sha256": hashlib.sha256(payload).hexdigest(),
        }
        accepted.write.mode("overwrite").parquet(str(directory / "accepted"))
        rejected.write.mode("overwrite").parquet(str(directory / "rejected"))
        if (
            spark.read.parquet(str(directory / "accepted")).count()
            != report["accepted"]
        ):
            raise ValueError("Parquet row count mismatch")
        (directory / "quality_report.json").write_text(
            json.dumps(report, indent=2), encoding="utf-8"
        )
        if not report["accepted"]:
            raise ValueError("No accepted rows; Azure publication blocked")
        if not args.local_raw and not args.local_only:
            # Content-specific versions: publish manifest last as completion marker.
            prefix = f'jobs/{run_hash}/{report["raw_sha256"]}/{uuid.uuid4().hex}'
            container = os.getenv("AZURE_PROCESSED_CONTAINER", "processed")
            manifest = {
                **report,
                "run_id": args.run_id,
                "raw_path": raw_path,
                "files": [],
            }
            try:
                with lake() as service:
                    for kind in ["accepted", "rejected"]:
                        for path in sorted((directory / kind).glob("*.parquet")):
                            content = path.read_bytes()
                            remote = f"{prefix}/{kind}/{path.name}"
                            file = service.get_file_client(container, remote)
                            file.upload_data(content, overwrite=True)
                            downloaded = file.download_file().readall()
                            if downloaded != content:
                                raise ValueError("Parquet verification mismatch")
                            manifest["files"].append(
                                {
                                    "path": remote,
                                    "bytes": len(content),
                                    "sha256": hashlib.sha256(content).hexdigest(),
                                }
                            )
                    service.get_file_client(
                        container, f"{prefix}/manifest.json"
                    ).upload_data(json.dumps(manifest).encode(), overwrite=True)
            except Exception as error:
                raise RuntimeError(
                    "Azure processed publication failed: " + type(error).__name__
                ) from None
            report["azure_manifest"] = f"{container}/{prefix}/manifest.json"
        (directory / "quality_report.json").write_text(
            json.dumps(report, indent=2), encoding="utf-8"
        )
        print(json.dumps(report))
    finally:
        spark.stop()


if __name__ == "__main__":
    main()
