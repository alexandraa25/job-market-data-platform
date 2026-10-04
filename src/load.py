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

    # Convert NaN / NaT values to None
    df = df.astype(object).where(pd.notnull(df), None)

    return df


def upsert_jobs(df, engine):

    df = prepare_for_database(df)

    logger.info("Starting PostgreSQL incremental UPSERT")

    inserted = 0
    updated = 0
    skipped = 0

    columns_to_compare = [
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

    with engine.begin() as connection:

        for record in records:

            existing = (
                connection.execute(select_sql, {"guid": record["guid"]})
                .mappings()
                .first()
            )

            # New job
            if existing is None:

                connection.execute(insert_sql, record)

                inserted += 1
                continue

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

            # Existing and identical
            else:
                skipped += 1

        sync_dimensions(connection, records)

    logger.info(
        "PostgreSQL UPSERT completed | " "Inserted: %s | Updated: %s | Skipped: %s",
        inserted,
        updated,
        skipped,
    )
    return {"inserted": inserted, "updated": updated, "skipped": skipped}
