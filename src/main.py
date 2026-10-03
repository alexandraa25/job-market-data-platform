import logging

from extract import (
    extract_jobs,
    save_raw_data
)

from transform import (
    transform_jobs,
    normalize_list_columns,
    add_primary_role,
    extract_skills,
    validate_jobs,
    save_processed_data
)

from load import (
    create_db_engine,
    test_connection,
    upsert_jobs
)

from logger_config import setup_logger


logger = logging.getLogger(__name__)


def main():

    logger.info("Starting ETL pipeline")

    # 1. EXTRACT
    data = extract_jobs(
        max_jobs_per_query=40
    )

    save_raw_data(data)

    # 2. TRANSFORM
    df = transform_jobs(data)

    df = normalize_list_columns(df)

    df = add_primary_role(df)

    df = extract_skills(df)

    # 3. VALIDATE
    validate_jobs(df)

    # 4. LOAD
    engine = create_db_engine()

    test_connection(engine)

    upsert_jobs(
        df,
        engine
    )

    # 5. SAVE PROCESSED DATA
    save_processed_data(df)

    logger.info(
        "ETL pipeline completed successfully"
    )


if __name__ == "__main__":
    setup_logger()
    main()