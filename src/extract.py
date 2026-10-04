import json
import logging
import time

from datetime import datetime
from pathlib import Path

import requests

logger = logging.getLogger(__name__)


SEARCH_URL = "https://himalayas.app/jobs/api/search"

SEARCH_QUERIES = [
    "data engineer",
    "data scientist",
    "data analyst",
    "machine learning engineer",
]


def extract_jobs(max_jobs_per_query=100):
    all_jobs = []

    logger.info("Starting targeted job extraction")

    for query in SEARCH_QUERIES:

        logger.info("Searching for query: %s", query)

        query_jobs = []
        page = 1

        while len(query_jobs) < max_jobs_per_query:

            params = {"q": query, "page": page, "sort": "recent"}

            logger.info("Fetching page %s for query '%s'", page, query)

            response = requests.get(SEARCH_URL, params=params, timeout=30)

            response.raise_for_status()

            data = response.json()

            jobs = data.get("jobs", [])

            # Stop if API returns no results
            if not jobs:

                logger.info("No more jobs found for query '%s'", query)

                break

            # Add the search query to every job
            for job in jobs:
                job["search_query"] = query

            query_jobs.extend(jobs)

            logger.info(
                "Received %s jobs for '%s' | " "Collected so far: %s",
                len(jobs),
                query,
                len(query_jobs),
            )

            page += 1

            # Small pause to avoid unnecessary API pressure
            time.sleep(0.3)

        # Keep only requested number
        query_jobs = query_jobs[:max_jobs_per_query]

        all_jobs.extend(query_jobs)

        logger.info(
            "Finished query '%s' | " "Collected %s jobs", query, len(query_jobs)
        )

    logger.info("Total jobs before deduplication: %s", len(all_jobs))

    # Remove duplicates using GUID
    unique_jobs = {}

    for job in all_jobs:

        guid = job.get("guid")

        if guid:

            if guid not in unique_jobs:

                unique_jobs[guid] = job

            else:

                # Job may appear in more than one search.
                # Preserve all matching queries.
                existing_query = unique_jobs[guid].get("search_query", "")

                new_query = job.get("search_query", "")

                existing_queries = set(existing_query.split(" | "))

                existing_queries.add(new_query)

                unique_jobs[guid]["search_query"] = " | ".join(sorted(existing_queries))

    jobs = list(unique_jobs.values())

    logger.info("Total jobs after deduplication: %s", len(jobs))

    return {"jobs": jobs, "totalCount": len(jobs)}


def save_raw_data(data):

    raw_folder = Path("data/raw")

    raw_folder.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    file_path = raw_folder / f"data_jobs_{timestamp}.json"

    with open(file_path, "w", encoding="utf-8") as file:

        json.dump(data, file, ensure_ascii=False, indent=4)

    logger.info("Raw data saved to: %s", file_path)

    return file_path
