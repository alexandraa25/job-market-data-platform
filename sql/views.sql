CREATE OR REPLACE VIEW data_engineer_jobs AS
SELECT guid,
       title,
       company_name,
       seniority,
       min_salary,
       max_salary,
       avg_salary,
       currency,
       has_python,
       has_sql,
       has_azure,
       has_aws,
       has_spark,
       has_pyspark,
       has_databricks,
       pub_date
FROM jobs
WHERE primary_role = 'Data Engineer';


SELECT *
FROM data_engineer_jobs;
