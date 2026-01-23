#!/bin/bash
set -e

echo "Starting WakaAgent Backend..."

# Wait for PostgreSQL to be ready
echo "Waiting for PostgreSQL..."
until pg_isready -h "${POSTGRES_HOST:-postgres}" -p "${POSTGRES_PORT:-5432}" -U "${POSTGRES_USER:-postgres}" > /dev/null 2>&1; do
  echo "PostgreSQL is unavailable - sleeping"
  sleep 1
done
echo "PostgreSQL is up"

# Skip migrations for celery worker
if [[ "$1" == "celery" ]]; then
    echo "Skipping database setup for celery worker"
else
    echo "Setting up database for migrations..."
    
    # Parse DATABASE_URL to extract connection details for fixing alembic_version column
    DB_URL="${DATABASE_URL:-postgresql://postgres:postgres@postgres:5432/wakaagent}"
    DB_URL="${DB_URL#postgresql+psycopg://}"
    DB_URL="${DB_URL#postgresql://}"
    
    # Extract components (format: user:password@host:port/dbname)
    if [[ "$DB_URL" =~ ^([^:]+):([^@]+)@([^:]+):([^/]+)/(.+)$ ]]; then
        DB_USER="${BASH_REMATCH[1]}"
        DB_PASS="${BASH_REMATCH[2]}"
        DB_HOST="${BASH_REMATCH[3]}"
        DB_PORT="${BASH_REMATCH[4]}"
        DB_NAME="${BASH_REMATCH[5]}"
        export PGPASSWORD="$DB_PASS"
    else
        DB_USER="postgres"
        DB_PASS="postgres"
        DB_HOST="postgres"
        DB_PORT="5432"
        DB_NAME="wakaagent"
        export PGPASSWORD="$DB_PASS"
    fi
    
    # Ensure alembic_version table exists with correct column size before migrations
    echo "Ensuring alembic_version table has correct column size..."
    psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" << 'EOF' 2>/dev/null
-- Create table if it doesn't exist with correct column size
CREATE TABLE IF NOT EXISTS alembic_version (
    version_num VARCHAR(64) NOT NULL,
    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);

-- If table exists with wrong column size, update it
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'alembic_version' 
        AND column_name = 'version_num'
        AND character_maximum_length < 64
    ) THEN
        ALTER TABLE alembic_version ALTER COLUMN version_num TYPE VARCHAR(64);
    END IF;
END $$;
EOF
    echo "alembic_version table ready"
    
    # Run Alembic migrations
    if command -v alembic >/dev/null 2>&1; then
        echo "Running database migrations..."
        alembic upgrade heads || echo "Warning: Migration failed, continuing anyway..."
    else
        echo "Warning: alembic command not found, skipping migrations"
    fi
    unset PGPASSWORD
fi

# Execute the main command
echo "Starting application..."
exec "$@"
