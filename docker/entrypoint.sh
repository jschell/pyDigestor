#!/bin/bash
set -e

echo "==> pyDigestor starting..."

# Check if using SQLite or PostgreSQL
if [ -n "$DATABASE_URL" ]; then
    if [[ $DATABASE_URL == sqlite* ]]; then
        echo "==> Using SQLite database"

        # Ensure data directory exists
        mkdir -p /app/data

        echo "==> Running database migrations..."
        uv run alembic upgrade head
        echo "==> Migrations complete!"

    elif [[ $DATABASE_URL == postgresql* ]]; then
        echo "==> Using PostgreSQL database"
        echo "==> Waiting for database..."

        # Extract host and port from DATABASE_URL
        DB_HOST=$(echo $DATABASE_URL | sed -n 's/.*@\([^:]*\):.*/\1/p')
        DB_PORT=$(echo $DATABASE_URL | sed -n 's/.*:\([0-9]*\)\/.*/\1/p')

        if [ -z "$DB_PORT" ]; then
            DB_PORT=5432
        fi

        echo "==> Checking database at $DB_HOST:$DB_PORT..."

        # Wait for PostgreSQL to be ready
        until nc -z "$DB_HOST" "$DB_PORT" 2>/dev/null; do
            echo "==> Database is unavailable - sleeping"
            sleep 1
        done

        echo "==> Database is up!"

        # Run migrations
        echo "==> Running database migrations..."
        uv run alembic upgrade head
        echo "==> Migrations complete!"
    fi
fi

echo "==> pyDigestor ready!"

# Execute the main command
exec "$@"
