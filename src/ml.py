"""Offline role classification: reviewed labels are required for training."""

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import random
import re
import unicodedata
import uuid

from src.transform import classify_role

ROLES = (
    "Data Engineer",
    "Data Analyst",
    "Data Scientist",
    "Machine Learning Engineer",
    "Other",
)


class PlainText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.ignored = 0

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


def clean_text(value):
    parser = PlainText()
    parser.feed(str(value or ""))
    parser.close()
    return re.sub(
        r"\s+", " ", unicodedata.normalize("NFKC", " ".join(parser.parts))
    ).strip()


def features(row):
    return clean_text(row.get("title")) + " " + clean_text(row.get("description"))


def text_hash(row):
    return hashlib.sha256(features(row).strip().lower().encode()).hexdigest()


def read_rows(path):
    return [
        json.loads(line)
        for line in Path(path).read_text(encoding="utf-8-sig").splitlines()
        if line.strip()
    ]


def write_rows(path, rows):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )


def prepare(rows, output, per_role=40, seed=42):
    if per_role < 1:
        raise ValueError("per_role must be positive")
    unique, guids, hashes = [], set(), set()
    for row in rows:
        guid = row.get("guid")
        if not guid or not clean_text(row.get("title")):
            raise ValueError("Every row requires guid and title")
        key = text_hash(row)
        if guid in guids or key in hashes:
            continue
        guids.add(guid)
        hashes.add(key)
        unique.append(
            {
                **row,
                "title": clean_text(row["title"]),
                "description": clean_text(row.get("description")),
                "text_hash": key,
                "rule_role": classify_role(row["title"]),
                "human_label": "",
                "label_source": "",
                "reviewed": False,
            }
        )
    buckets = defaultdict(list)
    for row in unique:
        buckets[row["rule_role"]].append(row)
    rng = random.Random(seed)
    queue = []
    for role in ROLES:
        bucket = sorted(buckets[role], key=lambda row: row["guid"])
        rng.shuffle(bucket)
        queue.extend(bucket[:per_role])
    rng.shuffle(queue)
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)  # Never overwrite reviewed annotations.
    write_rows(output / "review_queue.jsonl", queue)
    write_rows(output / "all_jobs.jsonl", unique)
    report = {
        "input_rows": len(rows),
        "unique_texts": len(unique),
        "duplicates_removed": len(rows) - len(unique),
        "rule_distribution": dict(Counter(row["rule_role"] for row in unique)),
        "review_queue_rows": len(queue),
        "review_distribution": dict(Counter(row["rule_role"] for row in queue)),
        "seed": seed,
        "sampling": "balanced by rule suggestion; not representative of market prevalence",
    }
    (output / "dataset_report.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    return report


def reviewed_rows(rows, min_per_class=10):
    if min_per_class < 2:
        raise ValueError("min_per_class must be at least 2")
    unique, by_guid, by_hash = [], {}, {}
    for row in rows:
        if row.get("reviewed") is not True:
            continue
        label = row.get("human_label")
        if row.get("label_source") != "human" or label not in ROLES:
            raise ValueError("Reviewed rows require a valid human label")
        guid = row.get("guid")
        if not guid or not clean_text(row.get("title")):
            raise ValueError("Reviewed rows require guid and title")
        key = text_hash(row)
        for existing in (by_guid.get(guid), by_hash.get(key)):
            if existing and existing != label:
                raise ValueError("Conflicting labels for the same job or text")
        if guid not in by_guid and key not in by_hash:
            unique.append(row)
        by_guid[guid] = label
        by_hash[key] = label
    counts = Counter(row["human_label"] for row in unique)
    missing = {role: counts[role] for role in ROLES if counts[role] < min_per_class}
    if missing:
        raise ValueError(
            f"Need at least {min_per_class} independently reviewed texts per class: {missing}"
        )
    return sorted(unique, key=lambda row: row["guid"])


def split_rows(rows, test_size=0.25, seed=42):
    from sklearn.model_selection import train_test_split

    if not 0.1 <= test_size <= 0.5:
        raise ValueError("test_size must be between 0.1 and 0.5")
    train, test = train_test_split(
        rows,
        test_size=test_size,
        random_state=seed,
        stratify=[row["human_label"] for row in rows],
    )
    if {text_hash(row) for row in train} & {text_hash(row) for row in test}:
        raise ValueError("Text leakage across train and test")
    if any(
        set(row["human_label"] for row in part) != set(ROLES) for part in (train, test)
    ):
        raise ValueError("Each class must be represented in train and test")
    return train, test


def train_model(rows, output_root, min_per_class=10, test_size=0.25, seed=42):
    import joblib
    import sklearn
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import classification_report, confusion_matrix, f1_score
    from sklearn.pipeline import Pipeline

    labelled = reviewed_rows(rows, min_per_class)
    train, test = split_rows(labelled, test_size, seed)
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
                    class_weight="balanced", max_iter=1000, random_state=seed
                ),
            ),
        ]
    )
    model.fit([features(row) for row in train], [row["human_label"] for row in train])
    actual = [row["human_label"] for row in test]
    predicted = model.predict([features(row) for row in test])
    baseline = [classify_role(row["title"]) for row in test]
    macro_f1 = float(
        f1_score(
            actual, predicted, labels=list(ROLES), average="macro", zero_division=0
        )
    )
    baseline_f1 = float(
        f1_score(actual, baseline, labels=list(ROLES), average="macro", zero_division=0)
    )
    version = (
        datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        + "-"
        + uuid.uuid4().hex[:8]
    )
    metadata = {
        "model_version": version,
        "status": "experimental",
        "sklearn_version": sklearn.__version__,
        "seed": seed,
        "label_source": "human",
        "reviewed_rows": len(labelled),
        "train_guids": [row["guid"] for row in train],
        "test_guids": [row["guid"] for row in test],
        "train_text_hashes": [text_hash(row) for row in train],
        "test_text_hashes": [text_hash(row) for row in test],
        "model_macro_f1": macro_f1,
        "rules_macro_f1": baseline_f1,
        "beats_rules_on_this_holdout": macro_f1 > baseline_f1,
        "model_report": classification_report(
            actual, predicted, labels=list(ROLES), output_dict=True, zero_division=0
        ),
        "rules_report": classification_report(
            actual, baseline, labels=list(ROLES), output_dict=True, zero_division=0
        ),
        "confusion_labels": list(ROLES),
        "confusion_matrix": confusion_matrix(
            actual, predicted, labels=list(ROLES)
        ).tolist(),
        "limitations": "Small balanced review sample; no automatic promotion. Holdout must not be reused for tuning.",
    }
    output = Path(output_root) / version
    output.mkdir(parents=True, exist_ok=False)
    joblib.dump({"model": model, "model_version": version}, output / "model.joblib")
    write_rows(
        output / "holdout_predictions.jsonl",
        [
            {
                "guid": row["guid"],
                "human_label": truth,
                "ml_role": pred,
                "rule_role": rule,
            }
            for row, truth, pred, rule in zip(test, actual, predicted, baseline)
        ],
    )
    (output / "evaluation.json").write_text(
        json.dumps(metadata, indent=2), encoding="utf-8"
    )
    (output / "manifest.json").write_text(
        json.dumps(
            {
                "model_version": version,
                "status": "experimental",
                "model_sha256": hashlib.sha256(
                    (output / "model.joblib").read_bytes()
                ).hexdigest(),
            }
        ),
        encoding="utf-8",
    )
    return output, metadata


def predict_rows(rows, model_path, output, threshold=0.55):
    import joblib

    if not 0 <= threshold <= 1:
        raise ValueError("threshold must be between 0 and 1")
    artifact = joblib.load(model_path)  # Only load trusted artifacts produced locally.
    model = artifact["model"]
    if not rows:
        write_rows(output, [])
        return 0
    probabilities = model.predict_proba([features(row) for row in rows])
    result = []
    for row, scores in zip(rows, probabilities):
        index = int(scores.argmax())
        score = float(scores[index])
        result.append(
            {
                "guid": row["guid"],
                "ml_role": str(model.classes_[index]),
                "ml_score": score,
                "needs_review": score < threshold,
                "model_version": artifact["model_version"],
                "rule_role": classify_role(row["title"]),
            }
        )
    write_rows(output, result)
    return len(result)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    prep = commands.add_parser("prepare")
    prep.add_argument("--input", required=True)
    prep.add_argument("--output", required=True)
    prep.add_argument("--per-role", type=int, default=40)
    train = commands.add_parser("train")
    train.add_argument("--labels", required=True)
    train.add_argument("--output", default="models")
    train.add_argument("--min-per-class", type=int, default=10)
    pred = commands.add_parser("predict")
    pred.add_argument("--input", required=True)
    pred.add_argument("--model", required=True)
    pred.add_argument("--output", required=True)
    args = parser.parse_args()
    try:
        if args.command == "prepare":
            print(
                json.dumps(
                    prepare(read_rows(args.input), args.output, args.per_role), indent=2
                )
            )
        elif args.command == "train":
            output, report = train_model(
                read_rows(args.labels), args.output, args.min_per_class
            )
            print(
                json.dumps(
                    {
                        "output": str(output),
                        "model_macro_f1": report["model_macro_f1"],
                        "rules_macro_f1": report["rules_macro_f1"],
                        "status": "experimental",
                    }
                )
            )
        else:
            print(
                json.dumps(
                    {
                        "predicted_rows": predict_rows(
                            read_rows(args.input), args.model, args.output
                        )
                    }
                )
            )
    except (ValueError, OSError) as error:
        parser.error(str(error))


if __name__ == "__main__":
    main()
