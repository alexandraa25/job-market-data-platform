-- Read-only presentation checks. Change this value for a different run.
\set demo_run_id 'manual__post_consolidation_20261014'
\pset pager off
BEGIN READ ONLY;

SELECT source, attempt, mode, status, extracted, error_type
FROM source_extraction_attempts
WHERE run_id = :'demo_run_id'
ORDER BY source, attempt;

SELECT source, status, accepted, rejected, inserted, updated, skipped, error_type
FROM source_load_runs
WHERE workflow_run_id = :'demo_run_id'
ORDER BY source;

SELECT source, job_count, company_count, jobs_with_salary, salary_coverage_pct
FROM analytics.source_summary
ORDER BY source;

SELECT count(*) AS stored_jobs,
       count(avg_salary) AS jobs_with_salary,
       round(100.0 * count(avg_salary) / NULLIF(count(*), 0), 1) AS salary_coverage_pct
FROM jobs;

SELECT count(*) AS duplicate_source_identities
FROM (
    SELECT source, source_job_id
    FROM jobs
    GROUP BY source, source_job_id
    HAVING count(*) > 1
) AS duplicates;

COMMIT;
