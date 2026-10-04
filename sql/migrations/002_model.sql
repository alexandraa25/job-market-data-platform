ALTER TABLE job_runs ADD COLUMN IF NOT EXISTS reconciled_at TIMESTAMPTZ;
CREATE TABLE IF NOT EXISTS companies (
    company_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name TEXT NOT NULL,
    name_key TEXT NOT NULL UNIQUE
);
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS company_id BIGINT REFERENCES companies(company_id);
CREATE INDEX IF NOT EXISTS jobs_company_id_idx ON jobs(company_id);
CREATE TABLE IF NOT EXISTS skills (
    skill_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name TEXT NOT NULL UNIQUE
);
CREATE TABLE IF NOT EXISTS job_skills (
    job_guid TEXT NOT NULL REFERENCES jobs(guid) ON DELETE CASCADE,
    skill_id BIGINT NOT NULL REFERENCES skills(skill_id),
    PRIMARY KEY(job_guid, skill_id)
);
CREATE INDEX IF NOT EXISTS job_skills_skill_id_idx ON job_skills(skill_id);
