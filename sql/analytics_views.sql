-- Apply after migrations 001 and 002. Regular views always read current jobs.

CREATE SCHEMA IF NOT EXISTS analytics;


CREATE OR REPLACE VIEW analytics.overview AS
SELECT count(*) AS total_jobs,
       count(DISTINCT company_id) AS total_companies,
       count(avg_salary) AS jobs_with_salary,
       count(*) - count(avg_salary) AS jobs_without_salary,
       round(100.0 * count(avg_salary) / NULLIF(count(*), 0), 2) AS salary_coverage_pct
FROM jobs;


CREATE OR REPLACE VIEW analytics.jobs_by_role AS
SELECT primary_role,
       count(*) AS job_count,
       count(avg_salary) AS jobs_with_salary,
       round(100.0 * count(avg_salary) / NULLIF(count(*), 0), 2) AS salary_coverage_pct
FROM jobs
GROUP BY primary_role;


CREATE OR REPLACE VIEW analytics.jobs_by_company AS
SELECT c.company_id,
       c.name AS company_name,
       count(*) AS job_count
FROM jobs j
JOIN companies c ON c.company_id=j.company_id
GROUP BY c.company_id,
         c.name;


CREATE OR REPLACE VIEW analytics.skills_by_role AS WITH role_totals AS
    (SELECT primary_role,
            count(*) AS role_job_count
     FROM jobs
     GROUP BY primary_role)
SELECT j.primary_role,
       s.skill_id,
       s.name AS skill,
       count(*) AS job_count,
       rt.role_job_count,
       round(100.0 * count(*) / NULLIF(rt.role_job_count, 0), 2) AS demand_pct
FROM jobs j
JOIN job_skills js ON js.job_guid=j.guid
JOIN skills s ON s.skill_id=js.skill_id
JOIN role_totals rt ON rt.primary_role IS NOT DISTINCT
FROM j.primary_role
GROUP BY j.primary_role,
         s.skill_id,
         s.name,
         rt.role_job_count;


CREATE OR REPLACE VIEW analytics.salary_by_role AS
SELECT primary_role,
       NULLIF(upper(btrim(currency)), '') AS currency,
       NULLIF(lower(btrim(salary_period)), '') AS salary_period,
       count(*) AS total_jobs,
       count(avg_salary) AS salary_sample_size,
       count(*)-count(avg_salary) AS jobs_without_salary,
       round(100.0 * count(avg_salary)/NULLIF(count(*), 0), 2) AS salary_coverage_pct,
       round(avg(avg_salary), 2) AS mean_advertised_salary,
       percentile_cont(0.5) WITHIN GROUP (
                                          ORDER BY avg_salary) AS median_advertised_salary,
                                         min(avg_salary) AS lowest_advertised_salary,
                                         max(avg_salary) AS highest_advertised_salary
FROM jobs
GROUP BY primary_role,
         NULLIF(upper(btrim(currency)), ''),
         NULLIF(lower(btrim(salary_period)), '');
