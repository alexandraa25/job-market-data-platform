import pandas as pd

from src.transform import (
    classify_role,
    normalize_list_columns,
    extract_skills,
    transform_jobs,
)


def test_classify_data_engineer():
    result = classify_role("Senior Data Engineer")

    assert result == "Data Engineer"


def test_classify_analytics_engineer():
    result = classify_role("Analytics Engineer")

    assert result == "Data Engineer"


def test_classify_data_scientist():
    result = classify_role("Junior Data Scientist")

    assert result == "Data Scientist"


def test_classify_machine_learning_engineer():
    result = classify_role("Machine Learning Engineer")

    assert result == "Machine Learning Engineer"


def test_classify_data_analyst():
    result = classify_role("Senior Data Analyst")

    assert result == "Data Analyst"


def test_classify_unknown_role():
    result = classify_role("Backend Developer")

    assert result == "Other"


def test_normalize_list_columns():
    df = pd.DataFrame(
        {
            "seniority": [["Senior"]],
            "locationRestrictions": [["Romania", "Germany"]],
            "categories": [["Data", "Engineering"]],
            "parentCategories": [["Technology"]],
        }
    )

    result = normalize_list_columns(df)

    assert result.loc[0, "seniority"] == "Senior"

    assert result.loc[0, "locationRestrictions"] == "Romania, Germany"

    assert result.loc[0, "categories"] == "Data, Engineering"


def test_extract_skills():
    df = pd.DataFrame(
        {
            "title": ["Data Engineer"],
            "description": [
                (
                    "We are looking for someone "
                    "with Python, SQL, Azure, "
                    "Databricks and Docker."
                )
            ],
        }
    )

    result = extract_skills(df)

    assert result.loc[0, "has_python"] == 1
    assert result.loc[0, "has_sql"] == 1
    assert result.loc[0, "has_azure"] == 1
    assert result.loc[0, "has_databricks"] == 1
    assert result.loc[0, "has_docker"] == 1

    assert result.loc[0, "has_aws"] == 0
    assert result.loc[0, "has_spark"] == 0


def test_extract_scikit_learn():
    df = pd.DataFrame(
        {
            "title": ["Data Scientist"],
            "description": ["Experience with scikit-learn required."],
        }
    )

    result = extract_skills(df)

    assert result.loc[0, "has_scikit_learn"] == 1


def test_transform_jobs():
    data = {
        "jobs": [
            {
                "guid": "job-123",
                "search_query": "data engineer",
                "title": "  Data Engineer  ",
                "companyName": " Test Company ",
                "employmentType": "Full Time",
                "minSalary": "50000",
                "maxSalary": "70000",
                "salaryPeriod": "annual",
                "seniority": ["Mid-level"],
                "currency": "USD",
                "locationRestrictions": ["Romania"],
                "categories": ["Data"],
                "parentCategories": ["Technology"],
                "description": "Python and SQL",
                "pubDate": 1760000000,
                "expiryDate": 1765000000,
                "applicationLink": "https://example.com",
            }
        ]
    }

    result = transform_jobs(data)

    assert len(result) == 1

    assert result.loc[0, "title"] == "Data Engineer"

    assert result.loc[0, "companyName"] == "Test Company"

    assert result.loc[0, "minSalary"] == 50000

    assert result.loc[0, "maxSalary"] == 70000

    assert result.loc[0, "avgSalary"] == 60000


def test_transform_removes_duplicate_guid():
    job = {
        "guid": "same-job",
        "search_query": "data engineer",
        "title": "Data Engineer",
        "companyName": "Company",
        "employmentType": "Full Time",
        "minSalary": None,
        "maxSalary": None,
        "salaryPeriod": "annual",
        "seniority": [],
        "currency": None,
        "locationRestrictions": [],
        "categories": [],
        "parentCategories": [],
        "description": "",
        "pubDate": 1760000000,
        "expiryDate": 1765000000,
        "applicationLink": "https://example.com",
    }

    data = {"jobs": [job, job.copy()]}

    result = transform_jobs(data)

    assert len(result) == 1
