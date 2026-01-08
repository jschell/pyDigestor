#!/bin/bash
# Native Python setup script for pyDigestor

set -e

echo "==> pyDigestor Native Setup"

# Check for Python 3.13
if ! command -v python3.13 &> /dev/null; then
    echo "ERROR: Python 3.13 not found"
    echo "Install: sudo apt install python3.13  # or brew install python@3.13"
    exit 1
fi

# Check for uv
if ! command -v uv &> /dev/null; then
    echo "ERROR: uv not found"
    echo "Install: curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

# Install dependencies
echo "==> Installing dependencies..."
uv sync

# Create data directory
echo "==> Creating data directory..."
mkdir -p data

# Copy config files if they don't exist
if [ ! -f .env ]; then
    echo "==> Creating .env from template..."
    cp .env.example .env
    echo "Edit .env to add your secrets (API keys, database credentials)"
fi

if [ ! -f config.toml ]; then
    echo "==> Creating config.toml from template..."
    cp config.example.toml config.toml
    echo "Edit config.toml to customize feeds and settings"
fi

# Run migrations
echo "==> Running database migrations..."
uv run alembic upgrade head

echo ""
echo "==> Setup complete!"
echo ""
echo "Usage:"
echo "  uv run pydigestor status        # Check status"
echo "  uv run pydigestor ingest        # Fetch articles"
echo "  uv run pydigestor search 'CVE'  # Search content"
echo ""
