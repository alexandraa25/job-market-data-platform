from contextlib import nullcontext
from decimal import Decimal
import logging
import os

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL

try:
    from .model import sync_dimensions
except ImportError:
    from model import sync_dimensions


logger = logging.getLogger(__name__)

load_dotenv()


def create_db_engine():

    connection_url = URL.create(
        drivername="postgresql+psycopg",
        username=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        host=os.getenv("DB_HOST"),
        port=int(os.getenv("DB_PORT")),
        database=os.getenv("DB_NAME"),
    )

    engine = create_engine(connection_url)

    return engine


def test_connection(engine):

    try:
        with engine.connect() as connection:

            result = connection.execute(text("SELECT version();"))

            version = result.fetchone()

            logger.info("Database connection successful")

            logger.info("PostgreSQL version: %s", version[0])

    except Exception:
        logger.exception("Database connection failed")

        raise


def prepare_for_database(df):
    df = df.copy()

    df = df.rename(
        columns={
            "companyName": "company_name",
            "employmentType": "employment_type",
            "minSalary": "min_salary",
            "maxSalary": "max_salary",
            "salaryPeriod": "salary_period",
            "locationRestrictions": "location_restrictions",
            "parentCategories": "parent_categories",
            "pubDate": "pub_date",
            "expiryDate": "expiry_date",
            "applicationLink": "application_link",
            "avgSalary": "avg_salary",
        }
    )

    # Legacy single-source batches remain compatible; new sources require provenance.
    if "source" not in df:
        if df["guid"].astype(str).str.startswith("arbeitnow:").any():
            raise ValueError("Arbeitnow batch requires explicit provenance")
        df["source"] = "himalayas"
        df["source_job_id"] = df["guid"]
        df["source_url"] = df["application_link"]
    for name in ("source", "source_job_id", "source_url"):
        if name not in df:
            raise ValueError("Incomplete source provenance")
    if (
        df[["source", "source_job_id"]].isna().any().any()
        or df["source"].astype(str).str.strip().eq("").any()
        or df["source_job_id"].astype(str).str.strip().eq("").any()
    ):
        raise ValueError("Source identity must be nonempty")
    if df.duplicated(["source", "source_job_id"]).any():
        raise ValueError("Duplicate source identity in batch")

    # Convert NaN / NaT values to None
    df = df.astype(object).where(pd.notnull(df), None)

    # PostgreSQL NUMERIC uses Decimal; compare using the same representation.
    for column in ("min_salary", "max_salary", "avg_salary"):
        df[column] = df[column].map(
            lambda value: Decimal(str(value)) if value is not None else None
        )

    return df


def upsert_jobs(df, engine, *, connection=None, by_source=None):

    df = prepare_for_database(df)

    logger.info("Starting PostgreSQL incremental UPSERT")

    inserted = 0
    updated = 0
    skipped = 0

    columns_to_compare = [
        "source",
        "source_job_id",
        "source_url",
        "search_query",
        "title",
        "company_name",
        "employment_type",
        "min_salary",
        "max_salary",
        "salary_period",
        "seniority",
        "currency",
        "location_restrictions",
        "categories",
        "parent_categories",
        "description",
        "pub_date",
        "expiry_date",
        "application_link",
        "avg_salary",
        "primary_role",
        "has_python",
        "has_sql",
        "has_azure",
        "has_aws",
        "has_gcp",
        "has_spark",
        "has_pyspark",
        "has_databricks",
        "has_snowflake",
        "has_airflow",
        "has_docker",
        "has_kubernetes",
        "has_power_bi",
        "has_tableau",
        "has_tensorflow",
        "has_pytorch",
        "has_scikit_learn",
    ]

    insert_sql = text("""
        INSERT INTO jobs (
            guid,
            source, source_job_id, source_url,
            search_query,
            title,
            company_name,
            employment_type,
            min_salary,
            max_salary,
            salary_period,
            seniority,
            currency,
            location_restrictions,
            categories,
            parent_categories,
            description,
            pub_date,
            expiry_date,
            application_link,
            avg_salary,
            primary_role,
            has_python,
            has_sql,
            has_azure,
            has_aws,
            has_gcp,
            has_spark,
            has_pyspark,
            has_databricks,
            has_snowflake,
            has_airflow,
            has_docker,
            has_kubernetes,
            has_power_bi,
            has_tableau,
            has_tensorflow,
            has_pytorch,
            has_scikit_learn
        )
        VALUES (
            :guid,
            :source, :source_job_id, :source_url,
            :search_query,
            :title,
            :company_name,
            :employment_type,
            :min_salary,
            :max_salary,
            :salary_period,
            :seniority,
            :currency,
            :location_restrictions,
            :categories,
            :parent_categories,
            :description,
            :pub_date,
            :expiry_date,
            :application_link,
            :avg_salary,
            :primary_role,
            :has_python,
            :has_sql,
            :has_azure,
            :has_aws,
            :has_gcp,
            :has_spark,
            :has_pyspark,
            :has_databricks,
            :has_snowflake,
            :has_airflow,
            :has_docker,
            :has_kubernetes,
            :has_power_bi,
            :has_tableau,
            :has_tensorflow,
            :has_pytorch,
            :has_scikit_learn
        )
    """)

    update_sql = text("""
        UPDATE jobs
        SET
            source = :source, source_job_id = :source_job_id, source_url = :source_url,
            search_query = :search_query,
            title = :title,
            company_name = :company_name,
            employment_type = :employment_type,
            min_salary = :min_salary,
            max_salary = :max_salary,
            salary_period = :salary_period,
            seniority = :seniority,
            currency = :currency,
            location_restrictions = :location_restrictions,
            categories = :categories,
            parent_categories = :parent_categories,
            description = :description,
            pub_date = :pub_date,
            expiry_date = :expiry_date,
            application_link = :application_link,
            avg_salary = :avg_salary,
            primary_role = :primary_role,
            has_python = :has_python,
            has_sql = :has_sql,
            has_azure = :has_azure,
            has_aws = :has_aws,
            has_gcp = :has_gcp,
            has_spark = :has_spark,
            has_pyspark = :has_pyspark,
            has_databricks = :has_databricks,
            has_snowflake = :has_snowflake,
            has_airflow = :has_airflow,
            has_docker = :has_docker,
            has_kubernetes = :has_kubernetes,
            has_power_bi = :has_power_bi,
            has_tableau = :has_tableau,
            has_tensorflow = :has_tensorflow,
            has_pytorch = :has_pytorch,
            has_scikit_learn = :has_scikit_learn,
            updated_at = CURRENT_TIMESTAMP
        WHERE guid = :guid
    """)

    select_sql = text("""
        SELECT *
        FROM jobs
        WHERE guid = :guid
    """)

    records = df.to_dict(orient="records")

    with (
        engine.begin() if connection is None else nullcontext(connection)
    ) as connection:

        for record in records:
            metrics = None
            if by_source is not None:
                metrics = by_source.setdefault(
                    record["source"], {"inserted": 0, "updated": 0, "skipped": 0}
                )

            existing = (
                connection.execute(select_sql, {"guid": record["guid"]})
                .mappings()
                .first()
            )

            # New job
            if existing is None:

                connection.execute(insert_sql, record)

                inserted += 1
                if metrics is not None:
                    metrics["inserted"] += 1
                continue

            if (existing["source"], existing["source_job_id"]) != (
                record["source"],
                record["source_job_id"],
            ):
                raise ValueError("Existing GUID cannot change source identity")

            # Check whether anything changed
            changed = False

            for column in columns_to_compare:

                old_value = existing[column]
                new_value = record[column]

                if old_value != new_value:
                    changed = True
                    break

            # Existing but modified
            if changed:

                connection.execute(update_sql, record)

                updated += 1
                if metrics is not None:
                    metrics["updated"] += 1

            # Existing and identical
            else:
                skipped += 1
                if metrics is not None:
                    metrics["skipped"] += 1

        sync_dimensions(connection, records)

    logger.info(
        "PostgreSQL UPSERT completed | " "Inserted: %s | Updated: %s | Skipped: %s",
        inserted,
        updated,
        skipped,
    )
    return {"inserted": inserted, "updated": updated, "skipped": skipped}
