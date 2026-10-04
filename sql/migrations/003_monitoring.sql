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
