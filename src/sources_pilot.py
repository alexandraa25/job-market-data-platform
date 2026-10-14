"""Offline multi-source transform/quality pilot; never loads DB or uploads Azure."""

import argparse
from collections import Counter
import json
from pathlib import Path

from src.sources.review import apply_reviews
from src.quality import assess_jobs
from src.sources.policy import select_job, POLICY_VERSION
from src.sources.adapters import (
    arbeitnow_row,
    himalayas_row,
    relevant_title,
    duplicate_candidates,
)
from src.transform import (
    transform_jobs,
    normalize_list_columns,
    add_primary_role,
    extract_skills,
)


def pilot(himalayas, pages, output, reviews=None):
    output = Path(output)
    if output.exists():
        raise ValueError("Use a new output directory; preserve previous results")
    source_rows = [himalayas_row(row) for row in himalayas["jobs"]]
    unique, duplicates = {}, 0
    for page in pages:
        if not isinstance(page.get("data"), list):
            raise ValueError("Arbeitnow snapshot data must be a list")
        for raw in page["data"]:
            row = arbeitnow_row(raw)
            if row["guid"] in unique:
                duplicates += 1
            else:
                unique[row["guid"]] = row
    candidates = [row for row in unique.values() if relevant_title(row["title"])]
    decisions = {row["guid"]: select_job(row["title"]) for row in unique.values()}
    apply_reviews(unique.values(), decisions, reviews or [])
    selected = [
        row for row in candidates if decisions[row["guid"]]["status"] == "include"
    ]
    review = [
        dict(row, selection=decisions[row["guid"]])
        for row in candidates
        if decisions[row["guid"]]["status"] == "review"
    ]
    rows = source_rows + selected
    if len({row["guid"] for row in rows}) != len(rows):
        raise ValueError("Source identities collide")
    if not rows:
        raise ValueError("No input jobs")
    frame = extract_skills(
        add_primary_role(normalize_list_columns(transform_jobs({"jobs": rows})))
    )
    provenance = {row["guid"]: row for row in rows}
    for name in (
        "source",
        "source_job_id",
        "source_url",
        "location_text",
        "remote",
        "source_tags",
    ):
        frame[name] = frame["guid"].map(lambda guid: provenance[guid][name])
    # The legacy Himalayas role rules remain unchanged.
    for index in frame.index[frame.source.eq("arbeitnow")]:
        frame.at[index, "primary_role"] = decisions[frame.at[index, "guid"]]["role"]
    accepted, rejected, quality = assess_jobs(frame)
    report = {
        "status": "offline pilot, no load",
        "himalayas_rows": len(source_rows),
        "arbeitnow_unique": len(unique),
        "arbeitnow_duplicates_removed": duplicates,
        "arbeitnow_title_candidates": len(candidates),
        "arbeitnow_selected": len(selected),
        "selection_policy": POLICY_VERSION,
        "snapshot_reviews_applied": len(reviews or []),
        "candidate_decisions": dict(
            Counter(decisions[row["guid"]]["status"] for row in candidates)
        ),
        "arbeitnow_filtered_out": len(unique) - len(candidates),
        "quality": quality,
        "accepted_by_source": dict(Counter(accepted.source)),
        "rejected_by_source": dict(Counter(rejected.source)),
        "roles_by_source": {
            source: dict(
                Counter(accepted.loc[accepted.source.eq(source), "primary_role"])
            )
            for source in ("himalayas", "arbeitnow")
        },
        "source_attribution": {"arbeitnow": "https://www.arbeitnow.com/"},
        "limitations": "Conservative title selection; ambiguous candidates are in review.json and are not quality rejections. No human-labelled relevance benchmark. Cross-source matches are review candidates, never automatically merged.",
    }
    output.mkdir(parents=True)
    accepted.to_json(
        output / "accepted.json", orient="records", date_format="iso", force_ascii=False
    )
    rejected.to_json(
        output / "rejected.json", orient="records", date_format="iso", force_ascii=False
    )
    (output / "quality_report.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    (output / "duplicate_candidates.json").write_text(
        json.dumps(duplicate_candidates(rows), indent=2), encoding="utf-8"
    )
    (output / "review.json").write_text(
        json.dumps(review, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    (output / "source_selection.json").write_text(
        json.dumps(
            [
                {"guid": row["guid"], "title": row["title"], **decisions[row["guid"]]}
                for row in unique.values()
            ],
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--himalayas", required=True)
    parser.add_argument("--arbeitnow", nargs="+", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument(
        "--review-decisions", help="Optional content-bound snapshot review JSON"
    )
    args = parser.parse_args()
    report = pilot(
        json.loads(Path(args.himalayas).read_text(encoding="utf-8-sig")),
        [
            json.loads(Path(path).read_text(encoding="utf-8-sig"))
            for path in args.arbeitnow
        ],
        args.output,
        (
            json.loads(Path(args.review_decisions).read_text(encoding="utf-8"))
            if args.review_decisions
            else None
        ),
    )
    print(json.dumps(report))


if __name__ == "__main__":
    main()
