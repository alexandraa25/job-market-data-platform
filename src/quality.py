"""Partition a transformed batch and retain explicit rejection reasons."""
import json
import logging
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)
ROLES = {"Data Engineer", "Data Scientist", "Data Analyst", "Machine Learning Engineer", "Other"}


def assess_jobs(df):
    required = {"guid", "title", "companyName", "minSalary", "maxSalary",
                "avgSalary", "pubDate", "expiryDate", "primary_role"}
    if required - set(df.columns):
        raise ValueError("Validation failed: missing columns: " + ", ".join(sorted(required - set(df.columns))))
    frame = df.reset_index(drop=True).copy()
    reasons = [[] for _ in range(len(frame))]

    def reject(mask, reason):
        for position in frame.index[mask.fillna(False)]:
            reasons[position].append(reason)

    for column in ("guid", "title", "companyName"):
        reject(frame[column].isna() | frame[column].astype(str).str.strip().eq(""), "missing_" + column)
    reject(frame.guid.duplicated(keep=False) & frame.guid.notna(), "duplicate_guid")
    for column in ("minSalary", "maxSalary", "avgSalary"):
        numeric = pd.to_numeric(frame[column], errors="coerce")
        reject(frame[column].notna() & numeric.isna(), "invalid_" + column)
        reject(numeric.lt(0) | numeric.isin([float("inf"), -float("inf")]), "invalid_" + column)
    reject(frame.minSalary.gt(frame.maxSalary), "salary_range_reversed")
    reject(frame.pubDate.isna(), "missing_or_invalid_pubDate")
    reject(frame.expiryDate.notna() & frame.expiryDate.lt(frame.pubDate), "expiry_before_publication")
    reject(~frame.primary_role.isin(ROLES), "invalid_primary_role")
    for column in frame.columns:
        if column.startswith("has_"):
            reject(~frame[column].isin([0, 1]), "invalid_" + column)
        if column.startswith("_dq_invalid_"):
            reject(frame[column].eq(True), column.removeprefix("_dq_"))
    clean = frame.drop(columns=[c for c in frame if c.startswith("_dq_")])
    bad = pd.Series([bool(items) for items in reasons], index=frame.index, dtype=bool)
    accepted = clean.loc[~bad].copy()
    rejected = clean.loc[bad].copy()
    rejected["rejection_reasons"] = [" | ".join(reasons[i]) for i in rejected.index]
    report = {"total": len(frame), "accepted": len(accepted), "rejected": len(rejected),
              "rejected_percent": round(100 * len(rejected) / len(frame), 2) if len(frame) else 0,
              "missing_percent": {c: round(100 * frame[c].isna().sum() / len(frame), 2)
                                  if len(frame) else 0 for c in sorted(required)},
              "reason_counts": {r: sum(r in items for items in reasons)
                                for r in sorted({r for items in reasons for r in items})}}
    return accepted, rejected, report


def validate_and_save(df, directory):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    accepted, rejected, report = assess_jobs(df)
    for filename, content in (("rejected.csv", rejected.to_csv(index=False)),
                              ("quality_report.json", json.dumps(report, indent=2))):
        path = directory / filename
        temporary = path.with_suffix(".tmp")
        temporary.write_text(content, encoding="utf-8")
        temporary.replace(path)
    logger.info("Data quality | Total: %s | Accepted: %s | Rejected: %s | Reasons: %s",
                report["total"], report["accepted"], report["rejected"], report["reason_counts"])
    if accepted.empty:
        raise ValueError("Validation failed: no accepted rows; see quality_report.json and rejected.csv")
    return accepted
