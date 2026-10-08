"""Train a fixed baseline on development labels, excluding a previous holdout."""

import argparse
from collections import Counter
import json
from pathlib import Path

from src.ml import read_rows, reviewed_rows, text_hash, train_model, write_rows


def development_rows(rows, previous_evaluation):
    labelled = reviewed_rows(rows)
    guids = set(previous_evaluation["test_guids"])
    hashes = set(previous_evaluation["test_text_hashes"])
    return [
        row
        for row in labelled
        if row["guid"] not in guids and text_hash(row) not in hashes
    ]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--labels", nargs="+", required=True)
    parser.add_argument("--previous-evaluation", required=True)
    parser.add_argument("--output", default="models")
    args = parser.parse_args()
    rows = [row for path in args.labels for row in read_rows(path)]
    previous = json.loads(Path(args.previous_evaluation).read_text())
    development = development_rows(rows, previous)
    output, report = train_model(development, args.output, seed=43)
    report.update(
        evaluation_scope="development validation; not independent final test",
        previous_model_version=previous["model_version"],
        excluded_previous_holdout=len(reviewed_rows(rows)) - len(development),
        label_distribution=dict(Counter(row["human_label"] for row in development)),
    )
    report[
        "limitations"
    ] += " Previous test was inspected and excluded. New sample emphasizes Other; metrics are not directly comparable with the first test."
    (output / "evaluation.json").write_text(json.dumps(report, indent=2))
    write_rows(output / "development_labels.jsonl", development)
    print(
        json.dumps(
            {
                key: report[key]
                for key in [
                    "model_version",
                    "reviewed_rows",
                    "excluded_previous_holdout",
                    "label_distribution",
                    "model_macro_f1",
                    "rules_macro_f1",
                    "evaluation_scope",
                ]
            }
        )
    )


if __name__ == "__main__":
    main()
