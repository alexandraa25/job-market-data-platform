-- Controlled fixtures in a schema created inside a transaction; always rolled back.
BEGIN;


CREATE SCHEMA analytics_validation;


SET LOCAL search_path TO analytics_validation;


CREATE TABLE jobs(guid text PRIMARY KEY,
                            company_id bigint,primary_role text,avg_salary numeric,currency text,salary_period text);


CREATE TABLE companies(company_id bigint PRIMARY KEY,
                                         name text);


CREATE TABLE skills(skill_id bigint PRIMARY KEY,
                                    name text);


CREATE TABLE job_skills(job_guid text,skill_id bigint,PRIMARY KEY(job_guid,
                                                                  skill_id));

-- Apply after migrations 001 and 002. Regular views always read current jobs.

CREATE OR REPLACE VIEW analytics_validation.overview AS
SELECT count(*) AS total_jobs,
       count(DISTINCT company_id) AS total_companies,
       count(avg_salary) AS jobs_with_salary,
       count(*) - count(avg_salary) AS jobs_without_salary,
       round(100.0 * count(avg_salary) / NULLIF(count(*), 0), 2) AS salary_coverage_pct
FROM jobs;


CREATE OR REPLACE VIEW analytics_validation.jobs_by_role AS
SELECT primary_role,
       count(*) AS job_count,
       count(avg_salary) AS jobs_with_salary,
       round(100.0 * count(avg_salary) / NULLIF(count(*), 0), 2) AS salary_coverage_pct
FROM jobs
GROUP BY primary_role;


CREATE OR REPLACE VIEW analytics_validation.jobs_by_company AS
SELECT c.company_id,
       c.name AS company_name,
       count(*) AS job_count
FROM jobs j
JOIN companies c ON c.company_id=j.company_id
GROUP BY c.company_id,
         c.name;


CREATE OR REPLACE VIEW analytics_validation.skills_by_role AS WITH role_totals AS
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


CREATE OR REPLACE VIEW analytics_validation.salary_by_role AS
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

DO $$ BEGIN
  IF (SELECT total_jobs FROM analytics_validation.overview) <> 0
     OR (SELECT salary_coverage_pct FROM analytics_validation.overview) IS NOT NULL THEN
    RAISE EXCEPTION 'Empty dataset coverage failed';
  END IF;
END $$;


INSERT INTO companies
VALUES (1,'Company');


INSERT INTO skills
VALUES (1,'python'),
       (2,'sql');


INSERT INTO jobs
VALUES ('a',1,'Data Engineer',100,'usd','annual'),
       ('b',1,'Data Engineer',200,' USD ','Annual'),
       ('c',1,'Data Engineer',NULL,NULL,'annual'),
       ('d',1,'Data Engineer',10,'USD','hourly'),
       ('e',1,'Data Engineer',300,'EUR','annual');


INSERT INTO job_skills
VALUES ('a',1),
       ('a',2),
       ('b',1);

DO $$ BEGIN
 IF (SELECT total_jobs FROM analytics_validation.overview) <> 5
    OR (SELECT jobs_without_salary FROM analytics_validation.overview) <> 1 THEN
   RAISE EXCEPTION 'Overview counts failed';
 END IF;
 IF (SELECT job_count FROM analytics_validation.jobs_by_company WHERE company_id=1) <> 5 THEN
   RAISE EXCEPTION 'Company counts multiplied by skills';
 END IF;
 IF (SELECT demand_pct FROM analytics_validation.skills_by_role WHERE skill='python') <> 40 THEN
   RAISE EXCEPTION 'Skill denominator must include jobs without detected skills';
 END IF;
 IF (SELECT mean_advertised_salary FROM analytics_validation.salary_by_role WHERE currency='USD' AND salary_period='annual') <> 150
    OR (SELECT salary_sample_size FROM analytics_validation.salary_by_role WHERE currency='USD' AND salary_period='annual') <> 2 THEN
   RAISE EXCEPTION 'Salary currencies/periods or normalization failed';
 END IF;
 IF (SELECT mean_advertised_salary FROM analytics_validation.salary_by_role WHERE currency IS NULL) IS NOT NULL THEN
   RAISE EXCEPTION 'Missing salaries must remain NULL';
 END IF;
END $$;


ROLLBACK;
