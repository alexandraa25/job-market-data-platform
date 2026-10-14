"""Read the public Arbeitnow API with bounded pagination and source-level deduplication."""

import time
from urllib.parse import urlparse

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

API_URL = "https://www.arbeitnow.com/api/job-board-api"


def fetch_jobs(max_pages=3, session=None):
    if not 1 <= max_pages <= 20:
        raise ValueError("max_pages must be between 1 and 20")
    owned = session is None
    if owned:
        session = requests.Session()
        retries = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"],
            respect_retry_after_header=True,
        )
        session.mount("https://", HTTPAdapter(max_retries=retries))
    url, seen_urls, jobs, page_reports = API_URL, set(), {}, []
    duplicates = 0
    try:
        for _ in range(max_pages):
            parsed = urlparse(url)
            if (
                parsed.scheme != "https"
                or parsed.netloc != "www.arbeitnow.com"
                or parsed.path != "/api/job-board-api"
            ):
                raise ValueError("Unexpected pagination URL")
            if url in seen_urls:
                raise ValueError("Pagination cycle detected")
            seen_urls.add(url)
            response = session.get(url, timeout=30)
            response.raise_for_status()
            data = response.json()
            rows = data.get("data")
            if not isinstance(rows, list):
                raise ValueError("API data must be a list")
            for row in rows:
                slug = row.get("slug")
                if not isinstance(slug, str) or not slug.strip():
                    raise ValueError("Every source row requires a nonempty slug")
                if slug in jobs:
                    duplicates += 1
                else:
                    jobs[slug] = row
            page_reports.append({"url": url, "rows": len(rows)})
            url = data.get("links", {}).get("next")
            if not url or not rows:
                break
            time.sleep(0.3)
        return {
            "data": list(jobs.values()),
            "extraction": {
                "pages": page_reports,
                "duplicates_removed": duplicates,
                "unique_rows": len(jobs),
                "truncated": bool(url),
            },
        }
    finally:
        if owned:
            session.close()
