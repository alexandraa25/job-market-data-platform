"""Compare text representations on shared development cross-validation folds."""

import argparse
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
import uuid

from src.ml import ROLES, clean_text, features, read_rows, text_hash
from src.ml_iteration import development_rows
from src.transform import classify_role


def compare(rows, previous, folds=5, seed=44):
    import numpy as np
    import sklearn
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import classification_report, f1_score
    from sklearn.model_selection import StratifiedGroupKFold
    from sklearn.pipeline import Pipeline

    development = development_rows(rows, previous)
    labels = np.array([row["human_label"] for row in development])
    # Identical normalized titles stay together, even if descriptions differ.
    groups = [clean_text(row["title"]).lower() for row in development]
    splitter = StratifiedGroupKFold(n_splits=folds, shuffle=True, random_state=seed)
    splits = list(splitter.split(development, labels, groups))
    results = {}
    assignments = []
    for train, valid in splits:
        if set(labels[train]) != set(ROLES) or set(labels[valid]) != set(ROLES):
            raise ValueError(
                "Each fold must contain all classes in train and validation"
            )
        assert not {groups[i] for i in train} & {groups[i] for i in valid}
        assignments.append(
            {
                "train_guids": [development[i]["guid"] for i in train],
                "validation_guids": [development[i]["guid"] for i in valid],
            }
        )
    extractors = {
        "title_only": lambda row: clean_text(row["title"]),
        "title_description": features,
    }
    for name, extract in extractors.items():
        texts = [extract(row) for row in development]
        predictions = [None] * len(development)
        scores = []
        for train, valid in splits:
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
            model.fit([texts[i] for i in train], labels[train])
            predicted = model.predict([texts[i] for i in valid])
            for i, prediction in zip(valid, predicted):
                predictions[i] = str(prediction)
            scores.append(
                float(
                    f1_score(
                        labels[valid],
                        predicted,
                        labels=list(ROLES),
                        average="macro",
                        zero_division=0,
                    )
                )
            )
        results[name] = {
            "fold_macro_f1": scores,
            "mean_macro_f1": float(np.mean(scores)),
            "std_macro_f1": float(np.std(scores)),
            "out_of_fold_report": classification_report(
                labels,
                predictions,
                labels=list(ROLES),
                output_dict=True,
                zero_division=0,
            ),
        }
    baseline = [classify_role(row["title"]) for row in development]
    results["rules"] = {
        "macro_f1": float(
            f1_score(
                labels, baseline, labels=list(ROLES), average="macro", zero_division=0
            )
        ),
        "report": classification_report(
            labels, baseline, labels=list(ROLES), output_dict=True, zero_division=0
        ),
    }
    return {
        "status": "experimental",
        "scope": "development model selection; not final independent test",
        "sklearn_version": sklearn.__version__,
        "seed": seed,
        "folds": folds,
        "grouping": "identical normalized titles; near-duplicates not guaranteed excluded",
        "development_rows": len(development),
        "label_distribution": dict(Counter(labels)),
        "excluded_previous_holdout": len(previous["test_guids"]),
        "development_text_hashes": [text_hash(row) for row in development],
        "assignments": assignments,
        "results": results,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--labels", nargs="+", required=True)
    parser.add_argument("--previous-evaluation", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    rows = [row for path in args.labels for row in read_rows(path)]
    report = compare(rows, json.loads(Path(args.previous_evaluation).read_text()))
    version = (
        datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        + "-"
        + uuid.uuid4().hex[:8]
    )
    output = Path(args.output) / version
    output.mkdir(parents=True, exist_ok=False)
    (output / "comparison.json").write_text(json.dumps(report, indent=2))
    print(
        json.dumps(
            {
                "output": str(output),
                "development_rows": report["development_rows"],
                "results": report["results"],
            }
        )
    )


if __name__ == "__main__":
    main()
