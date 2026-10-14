"""Apply explicit snapshot reviews; never generalize them to changed adverts."""

import hashlib
import json


def fingerprint(row):
    content = [row.get(key) for key in ("title", "companyName", "description")]
    return hashlib.sha256(
        json.dumps(content, ensure_ascii=False).encode("utf-8")
    ).hexdigest()


def apply_reviews(rows, decisions, reviews):
    by_id = {row["guid"]: row for row in rows}
    seen = set()
    allowed = {
        "Data Engineer",
        "Data Scientist",
        "Data Analyst",
        "Machine Learning Engineer",
    }
    for review in reviews:
        guid = review["guid"]
        if guid in seen or guid not in by_id:
            raise ValueError("Duplicate or unknown review identity")
        seen.add(guid)
        if review["fingerprint"] != fingerprint(by_id[guid]):
            raise ValueError("Stale review: advert content changed")
        if decisions[guid]["status"] != "review":
            raise ValueError("Reviews may only resolve ambiguous candidates")
        status, role = review["status"], review.get("role")
        if (
            status not in {"include", "exclude", "review"}
            or (status == "include" and role not in allowed)
            or (status != "include" and role is not None)
        ):
            raise ValueError("Invalid review status or role")
        if not review.get("reason") or not review.get("reviewer"):
            raise ValueError("Review requires reason and reviewer")
        decisions[guid] = {
            "status": status,
            "role": role,
            "reason": review["reason"],
            "policy_version": decisions[guid]["policy_version"],
            "decision_origin": review["reviewer"],
            "review_fingerprint": review["fingerprint"],
        }
    return decisions
