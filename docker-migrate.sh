#!/usr/bin/env bash
# Runs DB migrations from within a Docker container.
# Connects to postgres directly via environment variables.
# Used by the 'migrate' service in docker-compose.

set -euo pipefail

PSQL="psql postgresql://${DB_USER}:${DB_PASSWORD}@${DB_HOST:-postgres}:${DB_PORT:-5432}/${DB_NAME} -v ON_ERROR_STOP=1"

echo "=== RIO DB Migrations ==="

# Ensure schema_migrations table exists
$PSQL -c "
CREATE TABLE IF NOT EXISTS schema_migrations (
    version    TEXT PRIMARY KEY,
    applied_at TIMESTAMPTZ DEFAULT NOW()
);" > /dev/null

applied=0
skipped=0

for file in $(ls /migrations/*.sql | sort); do
    filename=$(basename "$file" .sql)

    exists=$($PSQL -tAc "SELECT 1 FROM schema_migrations WHERE version = '$filename'")

    if [[ "$exists" == "1" ]]; then
        echo "  ✓ $filename (already applied)"
        ((skipped++)) || true
    else
        echo "  → Applying $filename ..."
        $PSQL < "$file"
        $PSQL -c "INSERT INTO schema_migrations (version) VALUES ('$filename') ON CONFLICT DO NOTHING;" > /dev/null
        echo "  ✓ $filename done"
        ((applied++)) || true
    fi
done

echo ""
echo "Done: $applied applied, $skipped skipped."
