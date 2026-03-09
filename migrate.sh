#!/usr/bin/env bash
# Usage:
#   ./migrate.sh                           # local docker-compose.yml
#   ./migrate.sh -f docker-compose.prod.yml  # production

set -euo pipefail

COMPOSE_FILE=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        -f) COMPOSE_FILE="-f $2"; shift 2 ;;
        *)  echo "Unknown option: $1"; exit 1 ;;
    esac
done

PSQL="docker compose $COMPOSE_FILE exec -T postgres psql -U rio_user -d rio -v ON_ERROR_STOP=1"

echo "=== RIO DB Migrations ==="

# Ensure schema_migrations table exists
$PSQL -c "
CREATE TABLE IF NOT EXISTS schema_migrations (
    version    TEXT PRIMARY KEY,
    applied_at TIMESTAMPTZ DEFAULT NOW()
);" > /dev/null

MIGRATIONS_DIR="$(dirname "$0")/migrations"

applied=0
skipped=0

for file in $(ls "$MIGRATIONS_DIR"/*.sql | sort); do
    filename=$(basename "$file" .sql)

    # Check if already applied
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
