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

# Copy .env if not exists
if [ ! -f .env ]; then
    echo "==> Creating .env from template..."
    cp .env.example .env
    echo "Edit .env with your configuration if needed"
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
