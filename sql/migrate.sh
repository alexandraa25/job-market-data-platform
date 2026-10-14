#!/bin/sh
# Apply upgrades and views atomically; safe for both new and existing databases.
set -eu
sql_dir=$(CDPATH= cd "$(dirname "$0")" && pwd)
set -- -X -v ON_ERROR_STOP=1 --single-transaction
# Serialize concurrent initializers against the same business database.
set -- "$@" -c 'SELECT pg_advisory_xact_lock(736214001);'
for migration in "$sql_dir"/migrations/*.sql; do
    set -- "$@" -f "$migration"
done
set -- "$@" -f "$sql_dir/analytics_views.sql" -f "$sql_dir/source_analytics_views.sql"
exec psql "$@"
