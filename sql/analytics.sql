-- 1. Total number of jobs
SELECT
    COUNT(*) AS total_jobs
FROM jobs;


-- 2. Jobs by primary role
SELECT
    primary_role,
    COUNT(*) AS job_count
FROM jobs
GROUP BY primary_role
ORDER BY job_count DESC;


-- 3. Jobs by seniority
SELECT
    seniority,
    COUNT(*) AS job_count
FROM jobs
GROUP BY seniority
ORDER BY job_count DESC;


-- 4. Top companies
SELECT
    company_name,
    COUNT(*) AS job_count
FROM jobs
GROUP BY company_name
ORDER BY job_count DESC
LIMIT 10;


-- 5. Salary availability
SELECT
    COUNT(*) AS total_jobs,
    COUNT(avg_salary) AS jobs_with_salary,
    COUNT(*) - COUNT(avg_salary) AS jobs_without_salary,
    ROUND(
        100.0 * COUNT(avg_salary) / COUNT(*),
        2
    ) AS salary_coverage_pct
FROM jobs;


-- 6. Most requested skills
SELECT
    SUM(has_python) AS python,
    SUM(has_sql) AS sql,
    SUM(has_azure) AS azure,
    SUM(has_aws) AS aws,
    SUM(has_gcp) AS gcp,
    SUM(has_spark) AS spark,
    SUM(has_pyspark) AS pyspark,
    SUM(has_databricks) AS databricks,
    SUM(has_snowflake) AS snowflake,
    SUM(has_airflow) AS airflow,
    SUM(has_docker) AS docker,
    SUM(has_kubernetes) AS kubernetes,
    SUM(has_power_bi) AS power_bi,
    SUM(has_tableau) AS tableau,
    SUM(has_tensorflow) AS tensorflow,
    SUM(has_pytorch) AS pytorch,
    SUM(has_scikit_learn) AS scikit_learn
FROM jobs;


-- 7. Skills by role
SELECT
    primary_role,
    COUNT(*) AS jobs,
    SUM(has_python) AS python,
    SUM(has_sql) AS sql,
    SUM(has_azure) AS azure,
    SUM(has_aws) AS aws,
    SUM(has_spark) AS spark,
    SUM(has_databricks) AS databricks
FROM jobs
GROUP BY primary_role
ORDER BY jobs DESC;


-- 8. Cloud skill distribution
SELECT
    SUM(has_azure) AS azure_jobs,
    SUM(has_aws) AS aws_jobs,
    SUM(has_gcp) AS gcp_jobs
FROM jobs;


-- 9. Data Engineer jobs requiring Python + SQL
SELECT
    title,
    company_name,
    seniority
FROM jobs
WHERE primary_role = 'Data Engineer'
  AND has_python = 1
  AND has_sql = 1
ORDER BY pub_date DESC;


-- 10. Jobs requiring cloud + SQL
SELECT
    title,
    company_name,
    primary_role,
    has_azure,
    has_aws,
    has_gcp
FROM jobs
WHERE has_sql = 1
  AND (
      has_azure = 1
      OR has_aws = 1
      OR has_gcp = 1
  )
ORDER BY pub_date DESC;