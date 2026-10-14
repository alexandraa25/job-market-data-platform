-- Requires migrations 004-006. Stored historical postings, not active-job counts.
CREATE SCHEMA IF NOT EXISTS analytics;
CREATE OR REPLACE VIEW analytics.source_summary AS
SELECT source, count(*) AS job_count, count(DISTINCT company_id) AS company_count,
       count(avg_salary) AS jobs_with_salary,
       round(100.0*count(avg_salary)/NULLIF(count(*),0),2) AS salary_coverage_pct
FROM jobs GROUP BY source;
CREATE OR REPLACE VIEW analytics.source_roles AS
SELECT source, primary_role, count(*) AS job_count
FROM jobs GROUP BY source,primary_role;
CREATE OR REPLACE VIEW analytics.source_skills AS
SELECT j.source,j.primary_role,s.name AS skill,count(*) AS job_count
FROM jobs j JOIN job_skills js ON js.job_guid=j.guid
JOIN skills s ON s.skill_id=js.skill_id
GROUP BY j.source,j.primary_role,s.name;
