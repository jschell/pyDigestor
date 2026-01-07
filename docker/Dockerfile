FROM python:3.13-slim

# Install system dependencies for sqlite-vec compilation and CLI tools
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    sqlite3 \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Set working directory
WORKDIR /app

# Copy project files
COPY pyproject.toml .
COPY README.md .
COPY src ./src
COPY tests ./tests
COPY alembic ./alembic
COPY alembic.ini .

# Install dependencies with uv and clean cache to reduce image size
RUN uv sync && rm -rf /root/.cache/uv

# Create data directory for SQLite database
RUN mkdir -p /app/data

# Copy entrypoint script
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Set entrypoint
ENTRYPOINT ["/entrypoint.sh"]

# Default command (can be overridden)
CMD ["tail", "-f", "/dev/null"]
