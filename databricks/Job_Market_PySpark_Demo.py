# Databricks notebook source
raw_path = "/Volumes/workspace/default/raw/raw.json"

raw_df = (
    spark.read
    .option("multiLine", "true")
    .json(raw_path)
)

display(raw_df)

# COMMAND ----------

from pyspark.sql import functions as F

jobs_df = (
    raw_df
    .select(F.explode("jobs").alias("job"))
    .select("job.*")
)

print(f"Număr de joburi: {jobs_df.count()}")

display(
    jobs_df.select(
        "guid",
        "title",
        "companyName",
        "minSalary",
        "maxSalary",
        "currency",
        "pubDate",
    )
)

# COMMAND ----------

clean_df = (
    jobs_df
    .dropDuplicates(["guid"])
    .withColumn("title", F.trim(F.coalesce(F.col("title"), F.lit(""))))
    .withColumn(
        "companyName",
        F.trim(F.coalesce(F.col("companyName"), F.lit(""))),
    )
    .withColumn("minSalary", F.expr("try_cast(minSalary AS DOUBLE)"))
    .withColumn("maxSalary", F.expr("try_cast(maxSalary AS DOUBLE)"))
    .withColumn(
        "pubDate",
        F.timestamp_seconds(F.expr("try_cast(pubDate AS DOUBLE)")),
    )
    .withColumn(
        "expiryDate",
        F.timestamp_seconds(F.expr("try_cast(expiryDate AS DOUBLE)")),
    )
    .withColumn(
        "avgSalary",
        F.when(F.col("minSalary").isNull(), F.col("maxSalary"))
        .when(F.col("maxSalary").isNull(), F.col("minSalary"))
        .otherwise((F.col("minSalary") + F.col("maxSalary")) / 2),
    )
)

display(
    clean_df.select(
        "title",
        "companyName",
        "minSalary",
        "maxSalary",
        "avgSalary",
        "pubDate",
    )
)

# COMMAND ----------

title_lower = F.lower(F.col("title"))

classified_df = clean_df.withColumn(
    "primary_role",
    F.when(
        title_lower.contains("machine learning")
        | title_lower.contains("ml engineer"),
        "Machine Learning Engineer",
    )
    .when(title_lower.contains("data scientist"), "Data Scientist")
    .when(
        title_lower.contains("data engineer")
        | title_lower.contains("analytics engineer"),
        "Data Engineer",
    )
    .when(
        title_lower.contains("data analyst")
        | title_lower.contains("business intelligence"),
        "Data Analyst",
    )
    .otherwise("Other"),
)

display(
    classified_df
    .groupBy("primary_role")
    .count()
    .orderBy(F.desc("count"))
)

# COMMAND ----------

def missing_text(column):
    return (
        F.col(column).isNull()
        | (F.trim(F.col(column)) == "")
    )

rules = [
    (missing_text("guid"), "missing_guid"),
    (missing_text("title"), "missing_title"),
    (missing_text("companyName"), "missing_company"),
    (F.col("pubDate").isNull(), "missing_publication_date"),
    (F.col("minSalary") < 0, "negative_min_salary"),
    (F.col("maxSalary") < 0, "negative_max_salary"),
    (
        F.col("minSalary") > F.col("maxSalary"),
        "salary_range_reversed",
    ),
    (
        F.col("expiryDate") < F.col("pubDate"),
        "expiry_before_publication",
    ),
]

checked_df = classified_df.withColumn(
    "rejection_reasons",
    F.concat_ws(
        " | ",
        *[
            F.when(condition, F.lit(reason))
            for condition, reason in rules
        ],
    ),
)

accepted_df = checked_df.filter(
    F.col("rejection_reasons") == ""
).drop("rejection_reasons")

rejected_df = checked_df.filter(
    F.col("rejection_reasons") != ""
)

print(f"Acceptate: {accepted_df.count()}")
print(f"Respinse: {rejected_df.count()}")

display(rejected_df)

# COMMAND ----------

from uuid import uuid4

output_path = (
    "/Volumes/workspace/default/processed/"
    f"job_market/{uuid4().hex}/accepted"
)

accepted_count = accepted_df.count()

if accepted_count == 0:
    raise ValueError("Nu salvăm un batch fără rânduri acceptate.")

accepted_df.write.mode("overwrite").parquet(output_path)

saved_df = spark.read.parquet(output_path)
saved_count = saved_df.count()

if saved_count != accepted_count:
    raise ValueError("Numărul de rânduri salvate nu corespunde.")

print(f"Parquet verificat: {saved_count} rânduri")
print(f"Cale: {output_path}")

display(saved_df.select("title", "companyName", "primary_role"))