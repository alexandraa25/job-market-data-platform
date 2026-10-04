import logging
from pathlib import Path


def setup_logger():
    logs_folder = Path("logs")

    logs_folder.mkdir(parents=True, exist_ok=True)

    logging.basicConfig(
        level=logging.INFO,
        format=("%(asctime)s | " "%(levelname)s | " "%(name)s | " "%(message)s"),
        handlers=[
            logging.FileHandler("logs/pipeline.log", encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )
