-- Read-only examples. Counts represent stored jobs, including expired postings.

SELECT *
FROM analytics.overview;


SELECT *
FROM analytics.jobs_by_role
ORDER BY job_count DESC;


SELECT *
FROM analytics.jobs_by_company
ORDER BY job_count DESC,
         company_name
LIMIT 10;


SELECT *
FROM analytics.skills_by_role
ORDER BY primary_role,
         job_count DESC,
         skill;

-- Compare only a known currency + period; always inspect sample size.

SELECT *
FROM analytics.salary_by_role
WHERE currency='USD'
    AND salary_period='annual'
ORDER BY salary_sample_size DESC;
