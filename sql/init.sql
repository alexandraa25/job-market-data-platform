CREATE TABLE IF NOT EXISTS jobs (guid TEXT PRIMARY KEY,
                                           search_query TEXT, title TEXT, company_name TEXT, employment_type TEXT, min_salary NUMERIC, max_salary NUMERIC, salary_period TEXT, seniority TEXT, currency TEXT, location_restrictions TEXT, categories TEXT, parent_categories TEXT, description TEXT, pub_date TIMESTAMP, expiry_date TIMESTAMP, application_link TEXT, avg_salary NUMERIC, primary_role TEXT, has_python INTEGER, has_sql INTEGER, has_azure INTEGER, has_aws INTEGER, has_gcp INTEGER, has_spark INTEGER, has_pyspark INTEGER, has_databricks INTEGER, has_snowflake INTEGER, has_airflow INTEGER, has_docker INTEGER, has_kubernetes INTEGER, has_power_bi INTEGER, has_tableau INTEGER, has_tensorflow INTEGER, has_pytorch INTEGER, has_scikit_learn INTEGER, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);


CREATE DATABASE airflow;

CREATE TABLE IF NOT EXISTS job_runs (run_id TEXT PRIMARY KEY,
                                                 source TEXT NOT NULL,
                                                             started_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
                                                                                                     finished_at TIMESTAMPTZ,
                                                                                                     status TEXT NOT NULL CHECK (status IN ('running',
                                                                                                                                            'success',
                                                                                                                                            'failed')), last_stage TEXT NOT NULL,
                                                                                                                                                                        extracted INTEGER, accepted INTEGER, rejected INTEGER, inserted INTEGER, updated INTEGER, skipped INTEGER, quality_report_path TEXT, error_type TEXT);


CREATE TABLE IF NOT EXISTS job_run_attempts (run_id TEXT NOT NULL REFERENCES job_runs(run_id),
                                                                             stage TEXT NOT NULL,
                                                                                        attempt INTEGER NOT NULL,
                                                                                                        started_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
                                                                                                                                                finished_at TIMESTAMPTZ,
                                                                                                                                                status TEXT NOT NULL CHECK (status IN ('running',
                                                                                                                                                                                       'success',
                                                                                                                                                                                       'failed')), metrics JSONB NOT NULL DEFAULT '{}',
                                                                                                                                                                                                                                  error_type TEXT, PRIMARY KEY (run_id,
                                                                                                                                                                                                                                                                stage,
                                                                                                                                                                                                                                                                attempt));


ALTER TABLE job_runs ADD COLUMN IF NOT EXISTS reconciled_at TIMESTAMPTZ;


CREATE TABLE IF NOT EXISTS companies (company_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                                                                                     name TEXT NOT NULL,
                                                                                               name_key TEXT NOT NULL UNIQUE);


ALTER TABLE jobs ADD COLUMN IF NOT EXISTS company_id BIGINT REFERENCES companies(company_id);


CREATE INDEX IF NOT EXISTS jobs_company_id_idx ON jobs(company_id);


CREATE TABLE IF NOT EXISTS skills (skill_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                                                                                name TEXT NOT NULL UNIQUE);


CREATE TABLE IF NOT EXISTS job_skills
    (job_guid TEXT NOT NULL REFERENCES jobs(guid) ON DELETE CASCADE,
                                                            skill_id BIGINT NOT NULL REFERENCES skills(skill_id),
                                                                                                PRIMARY KEY(job_guid,
                                                                                                            skill_id));


CREATE INDEX IF NOT EXISTS job_skills_skill_id_idx ON job_skills(skill_id);


CREATE TABLE IF NOT EXISTS pipeline_alerts (run_id TEXT NOT NULL,
                                                        kind TEXT NOT NULL,
                                                                  status TEXT NOT NULL CHECK (status IN ('open',
                                                                                                         'resolved')), first_seen_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
                                                                                                                                                                  last_seen_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
                                                                                                                                                                                                            resolved_at TIMESTAMPTZ,
                                                                                                                                                                                                            details JSONB NOT NULL,
                                                                                                                                                                                                                          PRIMARY KEY(run_id,
                                                                                                                                                                                                                                      kind));


CREATE TABLE IF NOT EXISTS pipeline_daily_checks (expected_day DATE PRIMARY KEY,
                                                                    checked_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
                                                                                                            run_id TEXT, state TEXT NOT NULL,
                                                                                                                                    success_without_clear BOOLEAN NOT NULL,
                                                                                                                                                                  details JSONB NOT NULL);
