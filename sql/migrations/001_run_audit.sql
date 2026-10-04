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
