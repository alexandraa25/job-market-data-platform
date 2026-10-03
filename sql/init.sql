CREATE TABLE IF NOT EXISTS jobs (
    guid TEXT PRIMARY KEY,
    search_query TEXT,
    title TEXT,
    company_name TEXT,
    employment_type TEXT,

    min_salary NUMERIC,
    max_salary NUMERIC,
    salary_period TEXT,

    seniority TEXT,
    currency TEXT,

    location_restrictions TEXT,
    categories TEXT,
    parent_categories TEXT,

    description TEXT,

    pub_date TIMESTAMP,
    expiry_date TIMESTAMP,

    application_link TEXT,

    avg_salary NUMERIC,

    primary_role TEXT,

    has_python INTEGER,
    has_sql INTEGER,
    has_azure INTEGER,
    has_aws INTEGER,
    has_gcp INTEGER,
    has_spark INTEGER,
    has_pyspark INTEGER,
    has_databricks INTEGER,
    has_snowflake INTEGER,
    has_airflow INTEGER,
    has_docker INTEGER,
    has_kubernetes INTEGER,
    has_power_bi INTEGER,
    has_tableau INTEGER,
    has_tensorflow INTEGER,
    has_pytorch INTEGER,
    has_scikit_learn INTEGER,

    created_at TIMESTAMP
        DEFAULT CURRENT_TIMESTAMP,

    updated_at TIMESTAMP
        DEFAULT CURRENT_TIMESTAMP
);


CREATE DATABASE airflow;