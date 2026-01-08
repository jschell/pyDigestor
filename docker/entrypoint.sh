#!/bin/bash
set -e

echo "==> pyDigestor starting..."

# Create config files from templates if they don't exist
if [ ! -f /app/.env ] && [ -f /app/.env.example ]; then
    echo "==> Creating .env from template (.env.example)"
    cp /app/.env.example /app/.env
    echo "    Edit .env to add your secrets (API keys, database credentials)"
fi

if [ ! -f /app/config.toml ] && [ -f /app/config.example.toml ]; then
    echo "==> Creating config.toml from template (config.example.toml)"
    cp /app/config.example.toml /app/config.toml
    echo "    Edit config.toml to customize feeds and settings"
fi

# Check if using SQLite or PostgreSQL
if [ -n "$DATABASE_URL" ]; then
    if [[ $DATABASE_URL == sqlite* ]]; then
        echo "==> Using SQLite database"

        # Ensure data directory exists
        mkdir -p /app/data

        # Extract database file path from DATABASE_URL
        DB_FILE=$(echo $DATABASE_URL | sed 's|sqlite:///||')

        if [ ! -f "$DB_FILE" ]; then
            echo "==> Database file not found, initializing..."
        else
            echo "==> Database file exists at $DB_FILE"
        fi

        echo "==> Running database migrations..."
        uv run alembic upgrade head || {
            echo "==> ERROR: Migration failed!"
            exit 1
        }
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
