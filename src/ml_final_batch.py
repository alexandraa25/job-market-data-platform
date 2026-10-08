"""Reserve unseen API jobs for blind final evaluation; no DB or Azure writes."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import random
import re

from src.extract import extract_jobs
from src.ml import clean_text, read_rows, text_hash, write_rows


def reserve(rows, previous, limit=80, seed=45):
    guids = {row["guid"] for row in previous}
    hashes = {text_hash(row) for row in previous}
    titles = {clean_text(row["title"]).lower() for row in previous}
    candidates = []
    for row in sorted(rows, key=lambda item: item.get("guid", "")):
        guid = row.get("guid")
        title = clean_text(row.get("title"))
        key = text_hash(row)
        if (
            not guid
            or not title
            or not clean_text(row.get("description"))
            or guid in guids
            or key in hashes
            or title.lower() in titles
        ):
            continue
        guids.add(guid)
        hashes.add(key)
        titles.add(title.lower())
        candidates.append(
            {
                "guid": guid,
                "title": title,
                "description": clean_text(row["description"]),
                "company_name": row.get("companyName", ""),
                "human_label": "",
                "label_source": "",
                "reviewed": False,
            }
        )
    random.Random(seed).shuffle(candidates)
    return candidates[:limit], len(candidates)


def blind_page(template, rows):
    template = re.sub(
        r"<details>\s*<summary>Clasificarea regulilor existente.*?</details>",
        "",
        template,
        flags=re.S,
    )
    template = template.replace(
        "el('suggestion').textContent = row.rule_role || 'Indisponibila';", ""
    )
    template = template.replace("reviewed_labels.jsonl", "reviewed_final_labels.jsonl")
    payload = (
        json.dumps(rows, ensure_ascii=False)
        .replace("&", r"\u0026")
        .replace("<", r"\u003c")
        .replace(">", r"\u003e")
    )
    return template.replace(
        'type="application/json">[]', 'type="application/json">' + payload
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--previous", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    output = Path(args.output)
    if output.exists():
        parser.error("Output already exists; reserved data must not be overwritten")
    template = Path("ml/review.html").read_text(encoding="utf-8")
    snapshot = extract_jobs(max_jobs_per_query=100)
    rows, available = reserve(snapshot["jobs"], read_rows(args.previous))
    output.mkdir(parents=True, exist_ok=False)
    (output / "source_snapshot.json").write_text(
        json.dumps(snapshot, ensure_ascii=False)
    )
    write_rows(output / "reserved_jobs.jsonl", rows)
    report = {
        "reserved_at": datetime.now(timezone.utc).isoformat(),
        "seed": 45,
        "api_unique_rows": len(snapshot["jobs"]),
        "unseen_candidates": available,
        "reserved_rows": len(rows),
        "selection": "random from unseen targeted API search; no role stratification",
        "exclusions": "previous GUIDs, normalized full text and normalized titles",
        "scope": "reserved final evaluation; never add to training or tuning",
        "reserved_sha256": hashlib.sha256(
            (output / "reserved_jobs.jsonl").read_bytes()
        ).hexdigest(),
    }
    (output / "reservation.json").write_text(json.dumps(report, indent=2))
    if rows:
        (output / "review.html").write_text(
            blind_page(template, rows), encoding="utf-8"
        )
    print(json.dumps(report))


if __name__ == "__main__":
    main()
