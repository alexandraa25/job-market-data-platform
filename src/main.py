import logging
from uuid import uuid4

from logger_config import setup_logger
from stages import run_stage


def main():
    run_id = "manual_" + uuid4().hex
    logging.info("Starting ETL pipeline | run %s", run_id)
    for stage in ("extract", "transform", "validate", "load"):
        run_stage(stage, run_id, audit=True, source="manual")
    logging.info("ETL pipeline completed successfully | run %s", run_id)


if __name__ == "__main__":
    setup_logger()
    main()
