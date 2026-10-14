"""Explicit adapters to the existing transformation contract; no guessed salaries."""

import html
from html.parser import HTMLParser
import re
import unicodedata

COLUMNS = (
    "guid",
    "search_query",
    "title",
    "companyName",
    "employmentType",
    "minSalary",
    "maxSalary",
    "salaryPeriod",
    "seniority",
    "currency",
    "locationRestrictions",
    "categories",
    "parentCategories",
    "description",
    "pubDate",
    "expiryDate",
    "applicationLink",
)


class TextParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts, self.ignored = [], 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self.ignored += 1
        elif tag in ("p", "br", "li", "div"):
            self.parts.append(" ")

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self.ignored = max(0, self.ignored - 1)
        self.parts.append(" ")

    def handle_data(self, data):
        if not self.ignored:
            self.parts.append(data)


def plain_text(value):
    parser = TextParser()
    parser.feed(str(value or ""))
    parser.close()
    return re.sub(
        r"\s+", " ", unicodedata.normalize("NFKC", " ".join(parser.parts))
    ).strip()


def himalayas_row(row):
    if not row.get("guid"):
        raise ValueError("Himalayas guid required")
    result = {name: row.get(name) for name in COLUMNS}
    result.update(
        source="himalayas",
        source_job_id=str(row["guid"]),
        source_url=row.get("applicationLink"),
        location_text=None,
        remote=None,
        source_tags=[],
    )
    result["description"] = plain_text(result["description"])
    return result


def arbeitnow_row(row):
    slug = row.get("slug")
    if not isinstance(slug, str) or not slug.strip():
        raise ValueError("Arbeitnow slug required")
    types = row.get("job_types") or []
    if not isinstance(types, list) or not isinstance(row.get("tags") or [], list):
        raise ValueError("job_types and tags must be lists")
    result = {name: None for name in COLUMNS}
    result.update(
        guid="arbeitnow:" + slug,
        source="arbeitnow",
        source_job_id=slug,
        source_url=row.get("url"),
        search_query="arbeitnow-title-filter",
        title=row.get("title"),
        companyName=row.get("company_name"),
        employmentType=", ".join(types),
        description=plain_text(row.get("description")),
        pubDate=row.get("created_at"),
        applicationLink=row.get("url"),
        locationRestrictions=[],
        categories=[],
        parentCategories=[],
        seniority=[],
        location_text=row.get("location"),
        remote=row.get("remote"),
        source_tags=row.get("tags") or [],
    )
    return result


def relevant_title(title):
    # Broad candidate filter, not a confirmed role label; includes German variants.
    return bool(
        re.search(
            r"data|daten|machine learning|business intelligence|analytics",
            str(title or ""),
            re.I,
        )
    )


def duplicate_candidates(rows):
    buckets = {}
    for row in rows:
        key = tuple(
            re.sub(
                r"\s+",
                " ",
                unicodedata.normalize("NFKC", html.unescape(str(row.get(col) or ""))),
            )
            .lower()
            .strip()
            for col in ("title", "companyName")
        )
        if all(key):
            buckets.setdefault(key, []).append(row)
    return [
        {
            "title_company_key": list(key),
            "guids": [r["guid"] for r in group],
            "sources": sorted({r["source"] for r in group}),
            "action": "review_only",
        }
        for key, group in buckets.items()
        if len({r["source"] for r in group}) > 1
    ]
