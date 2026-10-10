CREATE TABLE IF NOT EXISTS source_extraction_attempts (
    run_id TEXT NOT NULL,
    source TEXT NOT NULL,
    attempt INTEGER NOT NULL,
    mode TEXT NOT NULL CHECK (mode IN ('snapshot','live')),
    status TEXT NOT NULL CHECK (status IN ('running','success','failed')),
    started_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    finished_at TIMESTAMPTZ,
    extracted INTEGER,
    snapshot_path TEXT,
    error_type TEXT,
    PRIMARY KEY(run_id,source,attempt)
);
ALTER TABLE source_load_runs ADD COLUMN IF NOT EXISTS workflow_run_id TEXT;
