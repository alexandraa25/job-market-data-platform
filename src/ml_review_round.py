"""Prepare a new human-review round without reusing previously proposed jobs."""

import argparse
from collections import Counter
import json
from pathlib import Path
import random

from src.ml import ROLES, read_rows, text_hash, write_rows


def select_round(rows, previous, per_role=20, other_count=60, seed=43):
    if per_role < 1 or other_count < 1:
        raise ValueError("Sample sizes must be positive")
    excluded_guids = {row["guid"] for row in previous}
    excluded_hashes = {text_hash(row) for row in previous}
    seen_guids, seen_hashes = set(), set()
    buckets = {role: [] for role in ROLES}
    for row in sorted(rows, key=lambda item: item["guid"]):
        key = text_hash(row)
        if (
            row["guid"] in excluded_guids
            or key in excluded_hashes
            or row["guid"] in seen_guids
            or key in seen_hashes
        ):
            continue
        seen_guids.add(row["guid"])
        seen_hashes.add(key)
        fresh = dict(row)
        fresh.update(human_label="", label_source="", reviewed=False)
        fresh.pop("reviewed_at", None)
        buckets[fresh["rule_role"]].append(fresh)
    rng = random.Random(seed)
    queue = []
    for role in ROLES:
        rng.shuffle(buckets[role])
        queue.extend(buckets[role][: other_count if role == "Other" else per_role])
    rng.shuffle(queue)
    return queue


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True)
    parser.add_argument("--previous", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    queue = select_round(read_rows(args.input), read_rows(args.previous))
    if not queue:
        parser.error("No unused examples remain")
    template = Path("ml/review.html").read_text(encoding="utf-8")
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=False)
    write_rows(output / "review_queue.jsonl", queue)
    report = {
        "rows": len(queue),
        "rule_distribution": dict(Counter(row["rule_role"] for row in queue)),
        "seed": 43,
        "sampling": "rule-stratified, emphasizes Other; not representative",
        "purpose": "additional development labels, not independent final evaluation",
    }
    (output / "dataset_report.json").write_text(json.dumps(report, indent=2))
    payload = (
        json.dumps(queue, ensure_ascii=False)
        .replace("&", r"\u0026")
        .replace("<", r"\u003c")
        .replace(">", r"\u003e")
    )
    template = template.replace(
        'type="application/json">[]', 'type="application/json">' + payload
    )
    template = template.replace("reviewed_labels.jsonl", "reviewed_labels_round2.jsonl")
    (output / "review.html").write_text(template, encoding="utf-8")
    print(json.dumps(report))


if __name__ == "__main__":
    main()
