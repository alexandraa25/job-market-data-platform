-- Existing records in this project were ingested from Himalayas.
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS source TEXT;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS source_job_id TEXT;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS source_url TEXT;
UPDATE jobs SET source = 'himalayas', source_job_id = guid, source_url = application_link
WHERE source IS NULL;
ALTER TABLE jobs ALTER COLUMN source SET NOT NULL;
ALTER TABLE jobs ALTER COLUMN source_job_id SET NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS jobs_source_identity_idx ON jobs(source, source_job_id);
