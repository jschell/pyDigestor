# Testing Instructions for Phase 1, Day 1-2

> **⚠️ HISTORICAL DOCUMENT**: This document describes the original PostgreSQL-based setup from early development (January 2026). The project has since migrated to SQLite with FTS5 search. For current testing instructions, see README.md and docs/quick start.md.

## What Was Completed

✅ All Phase 1, Day 1-2 tasks completed:
- Project directory structure
- pyproject.toml with dependencies
- Docker configuration (Dockerfile, docker-compose.yml, entrypoint.sh)
- Environment configuration (.env.example, .env)
- Database models (Article, TriageDecision, Signal)
- Database connection (database.py)
- Configuration module (config.py)
- Alembic migrations setup
- Initial database migration (001_initial_schema.py)
- Basic CLI with Typer (status, version, config commands)
- Pytest configuration and fixtures
- Initial test suite (test_database.py, test_models.py, test_config.py)
- README.md documentation

## Files Created

**Total: 20 Python files + 6 configuration files**

### Python Files
- src/pydigestor/__init__.py
- src/pydigestor/cli.py
- src/pydigestor/config.py
- src/pydigestor/database.py
- src/pydigestor/models.py
- src/pydigestor/sources/__init__.py
- src/pydigestor/steps/__init__.py
- src/pydigestor/utils/__init__.py
- tests/__init__.py
- tests/conftest.py
- tests/sources/__init__.py
- tests/steps/__init__.py
- tests/test_config.py
- tests/test_database.py
- tests/test_models.py
- alembic/env.py
- alembic/versions/001_initial_schema.py

### Configuration Files
- pyproject.toml
- alembic.ini
- docker/Dockerfile
- docker/docker-compose.yml
- docker/entrypoint.sh
- .env.example
- .env

### Documentation
- README.md
- TESTING.md (this file)

## Testing Steps (Local Environment)

Since Docker is not available in the current environment, these tests should be run locally:

### 1. Start Docker Containers

```bash
cd docker
docker compose up -d
```

**Expected output:**
```
Creating network "pydigestor-network"
Creating volume "docker_pgdata"
Creating pydigestor-db ... done
Creating pydigestor-app ... done
```

### 2. Check Container Logs

```bash
# View all logs
docker compose logs

# Follow app logs
docker compose logs -f app
```

**Expected output from app:**
```
==> pyDigestor starting...
==> Waiting for database...
==> Checking database at db:5432...
==> Database is up!
==> Running database migrations...
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade  -> 001, Initial schema
==> Migrations complete!
==> pyDigestor ready!
```

### 3. Verify Database Connection

```bash
# Access database directly
docker exec -it pydigestor-db psql -U pydigestor -d pydigestor

# Inside psql, run:
\dt  # List tables (should see articles, triage_decisions, signals)
\d articles  # Describe articles table
\q  # Quit
```

**Expected tables:**
- articles
- triage_decisions
- signals
- alembic_version

### 4. Test CLI Commands

```bash
# Show version
docker exec pydigestor-app uv run pydigestor version

# Show status
docker exec pydigestor-app uv run pydigestor status

# Show configuration
docker exec pydigestor-app uv run pydigestor config
```

**Expected output for status:**
```
pyDigestor Status

┌─────────────────────┬───────┐
│ Metric              │ Count │
├─────────────────────┼───────┤
│ Total Articles      │     0 │
│   Pending           │     0 │
│   Processed         │     0 │
│ Total Signals       │     0 │
│ Triage Decisions    │     0 │
└─────────────────────┴───────┘

Configuration

┌──────────────────────┬──────────────────┐
│ Setting              │ Value            │
├──────────────────────┼──────────────────┤
│ RSS Feeds            │                1 │
│ Reddit Subreddits    │                1 │
│ Triage Enabled       │                ✗ │
│ Extraction Enabled   │                ✗ │
│ Summarization Method │          lexrank │
└──────────────────────┴──────────────────┘
```

### 5. Run Tests

```bash
# Run all tests
docker exec pydigestor-app uv run pytest

# Run with verbose output
docker exec pydigestor-app uv run pytest -v

# Run with coverage
docker exec pydigestor-app uv run pytest --cov=src/pydigestor --cov-report=term-missing
```

**Expected output:**
```
========================= test session starts =========================
platform linux -- Python 3.13.x, pytest-7.x.x, pluggy-1.x.x
collected 11 items

tests/test_config.py ...                                        [ 27%]
tests/test_database.py ..                                       [ 45%]
tests/test_models.py ......                                     [100%]

========================= 11 passed in 0.XX s =========================
```

### 6. Verify Database Schema

```bash
# Check database schema matches models
docker exec pydigestor-app uv run python -c "
from pydigestor.database import engine
from sqlmodel import SQLModel, inspect

# Get table names
inspector = inspect(engine)
tables = inspector.get_table_names()
print('Tables:', tables)

# Check articles table columns
columns = [col['name'] for col in inspector.get_columns('articles')]
print('Articles columns:', columns)
"
```

**Expected output:**
```
Tables: ['alembic_version', 'articles', 'signals', 'triage_decisions']
Articles columns: ['id', 'source_id', 'url', 'title', 'content', 'summary', 'published_at', 'fetched_at', 'status', 'metadata']
```

## Validation Checklist

Phase 1, Day 1-2 is complete when:

- [ ] Docker containers start successfully (db + app)
- [ ] Database migrations run automatically on startup
- [ ] Database contains all three tables (articles, triage_decisions, signals)
- [ ] CLI commands work (`pydigestor status`, `pydigestor config`, `pydigestor version`)
- [ ] All tests pass (11 tests)
- [ ] Test coverage is >80%
- [ ] No errors in container logs

## Troubleshooting

### Issue: Containers don't start

**Check:**
```bash
docker compose ps
docker compose logs
```

**Common fixes:**
- Port 5432 already in use: Stop other PostgreSQL instances
- Build failed: Run `docker compose build --no-cache`

### Issue: Database connection fails

**Check:**
```bash
docker exec pydigestor-app env | grep DATABASE_URL
```

**Should be:**
```
DATABASE_URL=postgresql://pydigestor:pydigestor_dev@db:5432/pydigestor
```

### Issue: Migrations don't run

**Manually run migrations:**
```bash
docker exec pydigestor-app uv run alembic upgrade head
```

### Issue: Tests fail

**Check Python path:**
```bash
docker exec pydigestor-app uv run python -c "import sys; print(sys.path)"
```

**Reinstall dependencies:**
```bash
docker exec pydigestor-app uv sync
```

## Next Steps

After validating Phase 1, Day 1-2:

1. **Commit changes:**
   ```bash
   git add .
   git commit -m "feat: complete Phase 1 Day 1-2 project setup"
   git push origin feature/project-setup
   ```

2. **Move to Day 3-4:** RSS/Atom feed parsing
   - See `docs/IMPLEMENTATION_PLAN.md` for detailed tasks

## Notes

- Docker setup uses multi-container approach (db + app)
- Database data persists in Docker volume `docker_pgdata`
- Source code is mounted as volume for live development
- Tests use in-memory SQLite (not PostgreSQL) for speed
- LLM features are disabled in Phase 1 (ENABLE_TRIAGE=false, ENABLE_EXTRACTION=false)

## Success!

If all validation steps pass, Phase 1 Day 1-2 is **COMPLETE** ✅

The project foundation is solid and ready for RSS/Atom feed implementation.
