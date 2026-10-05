"""Databricks-compatible processing using the supplied managed Spark session."""

import hashlib
import json
import uuid
from .spark_process import raw_schema, transform_frame, partition


def process_cloud(spark, run_id, raw_root, processed_root, write_manifest):
    from pyspark.sql import functions as F, types as T

    if not run_id:
        raise ValueError("A raw-upload run ID is required")
    run_hash = hashlib.sha256(run_id.encode()).hexdigest()
    raw_path = f'{raw_root.rstrip("/")}/jobs/{run_hash}/raw.json'
    schema = T.StructType([T.StructField("jobs", T.ArrayType(raw_schema()))])
    raw = (
        spark.read.schema(schema)
        .option("multiLine", True)
        .option("mode", "FAILFAST")
        .json(raw_path)
    )
    rows = raw.select(F.posexplode("jobs").alias("_position", "job")).select(
        "_position", "job.*"
    )
    frame = transform_frame(rows)
    accepted, rejected = partition(frame)
    report = {
        "run_id": run_id,
        "input": rows.count(),
        "deduplicated": frame.count(),
        "accepted": accepted.count(),
        "rejected": rejected.count(),
        "raw_path": raw_path,
        "engine": "databricks-managed-spark",
    }
    if not report["accepted"]:
        raise ValueError("No accepted rows; publication blocked")
    prefix = (
        f'{processed_root.rstrip("/")}/databricks/jobs/{run_hash}/{uuid.uuid4().hex}'
    )
    for kind, df in [("accepted", accepted), ("rejected", rejected)]:
        path = f"{prefix}/{kind}"
        df.write.mode("overwrite").parquet(path)
        actual = spark.read.parquet(path)
        if (
            actual.count() != report[kind]
            or df.exceptAll(actual).limit(1).count()
            or actual.exceptAll(df).limit(1).count()
        ):
            raise ValueError("Parquet content verification failed: " + kind)
        report[kind + "_path"] = path
    report["manifest_path"] = prefix + "/manifest.json"
    write_manifest(report["manifest_path"], json.dumps(report, indent=2))
    return report

