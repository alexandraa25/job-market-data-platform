CREATE TABLE IF NOT EXISTS source_load_runs (
    run_id TEXT NOT NULL,
    source TEXT NOT NULL,
    started_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    finished_at TIMESTAMPTZ,
    status TEXT NOT NULL CHECK (status IN ('running', 'success', 'failed')),
    input_rows INTEGER NOT NULL CHECK (input_rows >= 0),
    accepted INTEGER CHECK (accepted >= 0),
    rejected INTEGER CHECK (rejected >= 0),
    inserted INTEGER CHECK (inserted >= 0),
    updated INTEGER CHECK (updated >= 0),
    skipped INTEGER CHECK (skipped >= 0),
    error_type TEXT,
    PRIMARY KEY (run_id, source)
);
