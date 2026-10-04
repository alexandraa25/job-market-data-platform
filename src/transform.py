import logging
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)


def transform_jobs(data):
    df = pd.DataFrame(data["jobs"])

    logger.info("Rows before transformation: %s", len(df))

    columns_to_keep = [
        "guid",
        "search_query",
        "title",
        "companyName",
        "employmentType",
        "minSalary",
        "maxSalary",
        "salaryPeriod",
        "seniority",
        "currency",
        "locationRestrictions",
        "categories",
        "parentCategories",
        "description",
        "pubDate",
        "expiryDate",
        "applicationLink",
    ]

    df = df[columns_to_keep].copy()

    # Remove duplicate jobs
    before_dedup = len(df)

    df = df.drop_duplicates(subset=["guid"])

    removed_duplicates = before_dedup - len(df)

    if removed_duplicates > 0:
        logger.warning("Removed %s duplicate jobs", removed_duplicates)

    # Clean text columns
    df["title"] = df["title"].fillna("").str.strip()

    df["companyName"] = df["companyName"].fillna("").str.strip()

    # Convert dates
    df["_dq_invalid_pubDate"] = (
        df["pubDate"].notna()
        & pd.to_datetime(df["pubDate"], unit="s", errors="coerce").isna()
    )

    df["pubDate"] = pd.to_datetime(df["pubDate"], unit="s", errors="coerce")

    df["_dq_invalid_expiryDate"] = (
        df["expiryDate"].notna()
        & pd.to_datetime(df["expiryDate"], unit="s", errors="coerce").isna()
    )

    df["expiryDate"] = pd.to_datetime(df["expiryDate"], unit="s", errors="coerce")

    # Convert salary columns to numeric
    df["_dq_invalid_minSalary"] = (
        df["minSalary"].notna() & pd.to_numeric(df["minSalary"], errors="coerce").isna()
    )

    df["minSalary"] = pd.to_numeric(df["minSalary"], errors="coerce")

    df["_dq_invalid_maxSalary"] = (
        df["maxSalary"].notna() & pd.to_numeric(df["maxSalary"], errors="coerce").isna()
    )

    df["maxSalary"] = pd.to_numeric(df["maxSalary"], errors="coerce")

    # Calculate average salary
    df["avgSalary"] = df[["minSalary", "maxSalary"]].mean(axis=1)

    logger.info("Rows after transformation: %s", len(df))

    return df


def normalize_list_columns(df):
    list_columns = [
        "seniority",
        "locationRestrictions",
        "categories",
        "parentCategories",
    ]

    for col in list_columns:
        df[col] = df[col].apply(lambda x: ", ".join(x) if isinstance(x, list) else x)

    logger.info("Normalized list-type columns")

    return df


def classify_role(title):
    title = title.lower()

    if "machine learning" in title or "ml engineer" in title:
        return "Machine Learning Engineer"

    if "data scientist" in title:
        return "Data Scientist"

    if "data engineer" in title or "analytics engineer" in title:
        return "Data Engineer"

    if "data analyst" in title or "business intelligence" in title:
        return "Data Analyst"

    return "Other"


def add_primary_role(df):
    df["primary_role"] = df["title"].apply(classify_role)

    logger.info("Primary role classification completed")

    logger.info("Role distribution: %s", df["primary_role"].value_counts().to_dict())

    return df


def extract_skills(df):
    skills = {
        "python": r"\bpython\b",
        "sql": r"\bsql\b",
        "azure": r"\bazure\b",
        "aws": r"\baws\b",
        "gcp": r"\bgcp\b",
        "spark": r"\bspark\b",
        "pyspark": r"\bpyspark\b",
        "databricks": r"\bdatabricks\b",
        "snowflake": r"\bsnowflake\b",
        "airflow": r"\bairflow\b",
        "docker": r"\bdocker\b",
        "kubernetes": r"\bkubernetes\b",
        "power_bi": r"\bpower bi\b",
        "tableau": r"\btableau\b",
        "tensorflow": r"\btensorflow\b",
        "pytorch": r"\bpytorch\b",
        "scikit_learn": r"\bscikit[- ]learn\b",
    }

    text = (df["title"].fillna("") + " " + df["description"].fillna("")).str.lower()

    for skill_name, pattern in skills.items():

        df[f"has_{skill_name}"] = text.str.contains(
            pattern, regex=True, na=False
        ).astype(int)

    skill_columns = [col for col in df.columns if col.startswith("has_")]

    skill_frequencies = {col: int(df[col].sum()) for col in skill_columns}

    logger.info("Skill extraction completed")

    logger.info("Skill frequencies: %s", skill_frequencies)

    return df


def validate_jobs(df):
    total_rows = len(df)

    missing_guids = df["guid"].isna().sum()

    duplicate_guids = df["guid"].duplicated().sum()

    missing_titles = (df["title"] == "").sum()

    missing_company_names = (df["companyName"] == "").sum()

    jobs_without_salary = df["avgSalary"].isna().sum()

    logger.info(
        "Data Quality Report | "
        "Total rows: %s | "
        "Missing GUIDs: %s | "
        "Duplicate GUIDs: %s | "
        "Missing titles: %s | "
        "Missing company names: %s | "
        "Jobs without salary: %s",
        total_rows,
        missing_guids,
        duplicate_guids,
        missing_titles,
        missing_company_names,
        jobs_without_salary,
    )

    if missing_guids > 0:
        logger.error("Found %s rows with missing GUIDs", missing_guids)

    if duplicate_guids > 0:
        logger.warning("Found %s duplicate GUIDs", duplicate_guids)

    if missing_titles > 0:
        logger.warning("Found %s jobs with missing titles", missing_titles)

    if missing_company_names > 0:
        logger.warning(
            "Found %s jobs with missing company names", missing_company_names
        )


def save_processed_data(df):
    processed_folder = Path("data/processed")

    processed_folder.mkdir(parents=True, exist_ok=True)

    file_path = processed_folder / "jobs_clean.csv"

    df.to_csv(file_path, index=False)

    logger.info("Processed data saved to: %s", file_path)

    return file_path
