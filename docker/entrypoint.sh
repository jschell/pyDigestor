#!/bin/bash
set -e

echo "==> pyDigestor starting..."

# Wait for database to be ready
if [ -n "$DATABASE_URL" ]; then
    echo "==> Waiting for database..."

    # Extract host and port from DATABASE_URL
    # Format: postgresql://user:pass@host:port/db
    DB_HOST=$(echo $DATABASE_URL | sed -n 's/.*@\([^:]*\):.*/\1/p')
    DB_PORT=$(echo $DATABASE_URL | sed -n 's/.*:\([0-9]*\)\/.*/\1/p')

    if [ -z "$DB_PORT" ]; then
        DB_PORT=5432
    fi

    echo "==> Checking database at $DB_HOST:$DB_PORT..."

    # Wait for PostgreSQL to be ready
    until pg_isready -h "$DB_HOST" -p "$DB_PORT" -U pydigestor 2>/dev/null; do
        echo "==> Database is unavailable - sleeping"
        sleep 1
    done

    echo "==> Database is up!"

    # Run migrations
    echo "==> Running database migrations..."
    uv run alembic upgrade head

    echo "==> Migrations complete!"
fi

echo "==> pyDigestor ready!"

# Execute the main command
exec "$@"
