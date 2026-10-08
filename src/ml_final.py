"""One-time evaluation of the preselected title-only model on a reserved batch."""

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

from src.ml import ROLES, clean_text, read_rows, reviewed_rows, text_hash, write_rows
from src.transform import classify_role


def validate_final(rows, reserved, development):
    originals = {row["guid"]: row for row in reserved}
    if len(originals) != len(reserved):
        raise ValueError("Reserved GUIDs must be unique")
    seen = set()
    labelled = []
    for row in rows:
        guid = row.get("guid")
        if guid in seen or guid not in originals:
            raise ValueError("Final labels must contain unique reserved GUIDs only")
        seen.add(guid)
        if (
            row.get("title") != originals[guid]["title"]
            or row.get("description") != originals[guid]["description"]
        ):
            raise ValueError("Reserved text has changed")
        if row.get("reviewed") is True:
            if (
                row.get("label_source") != "human"
                or row.get("human_label") not in ROLES
            ):
                raise ValueError("Invalid human label")
            labelled.append(row)
    if seen != set(originals):
        raise ValueError(
            "Export must retain every reserved row, including skipped rows"
        )
    if not labelled:
        raise ValueError("No reviewed final labels")
    for key in (
        lambda row: row["guid"],
        text_hash,
        lambda row: clean_text(row["title"]).lower(),
    ):
        if {key(row) for row in reserved} & {key(row) for row in development}:
            raise ValueError("Final batch overlaps development")
    return labelled


def run(development_path, reserved_path, reservation_path, labels_path, output_path):
    import joblib
    import sklearn
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import classification_report, confusion_matrix
    from sklearn.pipeline import Pipeline

    output = Path(output_path)
    if output.exists():
        raise ValueError(
            "Final evaluation directory already exists; do not rerun or tune on final labels"
        )
    development = reviewed_rows(read_rows(development_path))
    if len(development) != 203:
        raise ValueError("Frozen protocol requires 203 development examples")
    reservation = json.loads(Path(reservation_path).read_text())
    reserved_bytes = Path(reserved_path).read_bytes()
    if hashlib.sha256(reserved_bytes).hexdigest() != reservation["reserved_sha256"]:
        raise ValueError("Reservation hash mismatch")
    reserved = read_rows(reserved_path)
    output.mkdir(parents=True, exist_ok=False)
    model = Pipeline(
        [
            (
                "tfidf",
                TfidfVectorizer(
                    ngram_range=(1, 2), max_features=30000, sublinear_tf=True
                ),
            ),
            (
                "classifier",
                LogisticRegression(
                    class_weight="balanced", max_iter=1000, random_state=44
                ),
            ),
        ]
    )
    model.fit(
        [clean_text(row["title"]) for row in development],
        [row["human_label"] for row in development],
    )
    version = output.name
    joblib.dump(
        {"model": model, "model_version": version, "feature_mode": "title_only"},
        output / "model.joblib",
    )
    manifest = {
        "model_version": version,
        "status": "experimental",
        "feature_mode": "title_only",
        "frozen_at": datetime.now(timezone.utc).isoformat(),
        "seed": 44,
        "model_sha256": hashlib.sha256(
            (output / "model.joblib").read_bytes()
        ).hexdigest(),
        "development_sha256": hashlib.sha256(
            Path(development_path).read_bytes()
        ).hexdigest(),
        "reservation_sha256": reservation["reserved_sha256"],
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2))
    # Freeze the candidate before reading final human labels.
    final = validate_final(read_rows(labels_path), reserved, development)
    actual = [row["human_label"] for row in final]
    predicted = model.predict([clean_text(row["title"]) for row in final])
    rules = [classify_role(row["title"]) for row in final]
    report = {
        "status": "experimental",
        "scope": "reserved final batch; evaluated once",
        "sklearn_version": sklearn.__version__,
        "model_version": version,
        "development_rows": len(development),
        "reserved_rows": len(reserved),
        "reviewed_rows": len(final),
        "skipped_rows": len(reserved) - len(final),
        "label_distribution": dict(Counter(actual)),
        "labels_sha256": hashlib.sha256(Path(labels_path).read_bytes()).hexdigest(),
        "model_report": classification_report(
            actual, predicted, labels=list(ROLES), output_dict=True, zero_division=0
        ),
        "rules_report": classification_report(
            actual, rules, labels=list(ROLES), output_dict=True, zero_division=0
        ),
        "confusion_labels": list(ROLES),
        "model_confusion_matrix": confusion_matrix(
            actual, predicted, labels=list(ROLES)
        ).tolist(),
        "rules_confusion_matrix": confusion_matrix(
            actual, rules, labels=list(ROLES)
        ).tolist(),
        "limitations": "Small targeted same-source batch; single human reviewer; near-duplicates may remain. No automatic promotion.",
    }
    report["model_accuracy"] = sum(a == b for a, b in zip(actual, predicted)) / len(
        actual
    )
    report["rules_accuracy"] = sum(a == b for a, b in zip(actual, rules)) / len(actual)
    report["model_macro_f1"] = report["model_report"]["macro avg"]["f1-score"]
    report["rules_macro_f1"] = report["rules_report"]["macro avg"]["f1-score"]
    write_rows(
        output / "final_predictions.jsonl",
        [
            dict(guid=row["guid"], human_label=a, ml_role=str(b), rule_role=c)
            for row, a, b, c in zip(final, actual, predicted, rules)
        ],
    )
    (output / "evaluation.json").write_text(json.dumps(report, indent=2))
    print(
        json.dumps(
            {
                key: report[key]
                for key in [
                    "model_version",
                    "reviewed_rows",
                    "skipped_rows",
                    "label_distribution",
                    "model_accuracy",
                    "rules_accuracy",
                    "model_macro_f1",
                    "rules_macro_f1",
                ]
            }
        )
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--development", required=True)
    parser.add_argument("--reserved", required=True)
    parser.add_argument("--reservation", required=True)
    parser.add_argument("--labels", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    run(args.development, args.reserved, args.reservation, args.labels, args.output)


if __name__ == "__main__":
    main()
