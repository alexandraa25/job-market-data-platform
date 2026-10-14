DO $$
BEGIN
    IF (SELECT count(*) FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'jobs'
          AND column_name IN ('source', 'source_job_id') AND is_nullable = 'NO') <> 2 THEN
        RAISE EXCEPTION 'Required source identity columns are missing or nullable';
    END IF;
    IF to_regclass('public.source_load_runs') IS NULL
       OR to_regclass('public.source_extraction_attempts') IS NULL
       OR to_regclass('public.jobs_source_identity_idx') IS NULL
       OR to_regclass('analytics.source_summary') IS NULL
       OR to_regclass('analytics.source_roles') IS NULL
       OR to_regclass('analytics.source_skills') IS NULL
       OR to_regclass('analytics.overview') IS NULL THEN
        RAISE EXCEPTION 'Bootstrap did not install the complete schema and views';
    END IF;
    IF EXISTS (SELECT 1 FROM jobs WHERE guid = 'bootstrap-legacy')
       AND NOT EXISTS (SELECT 1 FROM jobs WHERE guid = 'bootstrap-legacy'
           AND source = 'himalayas' AND source_job_id = 'bootstrap-legacy'
           AND source_url = 'https://example.com/legacy') THEN
        RAISE EXCEPTION 'Upgrade did not preserve the legacy identity and URL';
    END IF;
END $$;
