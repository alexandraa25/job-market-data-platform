"""Conservative Arbeitnow title policy; ambiguous candidates require review."""

import re
from src.sources.adapters import relevant_title

POLICY_VERSION = "arbeitnow-title-v1"


def select_job(title):
    text = str(title or "").casefold()

    def decision(status, reason, role=None):
        return {
            "status": status,
            "reason": reason,
            "role": role,
            "policy_version": POLICY_VERSION,
        }

    if not relevant_title(text):
        return decision("exclude", "outside_candidate_filter")
    if re.search(
        r"data protection|datenschutz|data\s*cent(?:er|re)|datacenter|pre[- ]sales|medical data officer|clinical data.*quality",
        text,
    ):
        return decision("exclude", "privacy_sales_clinical_or_physical_infrastructure")
    if re.search(
        r"\b(director|manager|head|leadership)\b|unit lead|architect|consultant|product manager",
        text,
    ):
        return decision("review", "management_consulting_or_architecture")
    roles = (
        (r"machine learning|\bml engineer\b", "Machine Learning Engineer"),
        (r"data scientist", "Data Scientist"),
        (
            r"data (?:platform )?engineer|analytics engineer|dateningenieur",
            "Data Engineer",
        ),
        (r"data analyst|analyste data|business intelligence analyst", "Data Analyst"),
    )
    for pattern, role in roles:
        if re.search(pattern, text):
            return decision("include", "explicit_core_role_title", role)
    return decision("review", "mixed_or_unrecognized_data_role")
