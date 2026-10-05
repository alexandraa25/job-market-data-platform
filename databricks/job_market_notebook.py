# Databricks notebook source
# MAGIC %md
# MAGIC # Job Market: raw → Parquet on Databricks
# MAGIC Requires Unity Catalog external volumes and a Spark-enabled compute.
# MAGIC Import this notebook under the repository's databricks directory.
# MAGIC No storage secrets are embedded; Unity Catalog supplies managed identity access.

# COMMAND ----------
import sys
from pathlib import Path

# Databricks Git folder/import: src must be next to databricks in the repo root.
sys.path.insert(0, str(Path.cwd().parent))
from src.cloud_process import process_cloud

# COMMAND ----------
dbutils.widgets.text("run_id", "")
dbutils.widgets.text("raw_volume", "/Volumes/job_market/default/raw")
dbutils.widgets.text("processed_volume", "/Volumes/job_market/default/processed")
run_id = dbutils.widgets.get("run_id")
raw_root = dbutils.widgets.get("raw_volume")
processed_root = dbutils.widgets.get("processed_volume")
for path in (raw_root, processed_root):
    if not path.startswith("/Volumes/") or len(path.rstrip("/").split("/")) != 5:
        raise ValueError(
            "Use a Unity Catalog volume root: /Volumes/catalog/schema/volume"
        )

# COMMAND ----------
# Use the Databricks-provided Spark session; no local master or spark.stop().
spark.conf.set("spark.sql.session.timeZone", "UTC")
result = process_cloud(
    spark,
    run_id,
    raw_root,
    processed_root,
    lambda path, content: dbutils.fs.put(path, content, overwrite=False),
)
print(result)
dbutils.notebook.exit(__import__("json").dumps(result))
