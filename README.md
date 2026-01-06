# pyDigestor

Feed aggregation and analysis pipeline that ingests RSS/Atom/Reddit feeds, extracts insights using local and LLM-based processing, and stores structured summaries in a queryable database.

## Overview

pyDigestor implements a 5-step pipeline:
1. **Ingest** - Fetch feeds (RSS/Atom/Reddit), extract target URLs
2. **Triage** - Fast LLM filter (keep/discard)
3. **Extract** - Pull structured insights/signals
4. **Summarize** - Local extractive summarization (TextRank/LexRank)
5. **Store** - Save to queryable database

## Key Features

- **Feed-agnostic**: Unified handling of RSS, Atom, and Reddit JSON
- **Local-first summarization**: 80% cost savings vs LLM-only
- **Pattern-based extraction**: Fast-path for known sites (GitHub, PDFs, arXiv)
- **Cost-optimized**: ~$0.42/month for LLM usage
- **Security-focused**: Optimized for r/netsec and r/blueteamsec
- **Docker-based**: Multi-container setup with PostgreSQL

## Quick Start (Docker)

```bash
# Clone repository
git clone https://github.com/youruser/pyDigestor.git
cd pyDigestor

# Configure environment
cp .env.example .env
# Edit .env if needed (defaults work for local development)

# Start Docker containers
cd docker
docker-compose up -d

# Wait for containers to start and migrations to run
docker-compose logs -f app

# Check status
docker exec pydigestor-app uv run pydigestor status

# Run tests
docker exec pydigestor-app uv run pytest
```

See [docs/IMPLEMENTATION_PLAN.md](docs/IMPLEMENTATION_PLAN.md) for detailed setup instructions.

## Architecture

```
RSS/Atom Feeds + Reddit → Parse → Extract URLs
    ↓
Content Extraction (PDF, GitHub, arXiv, blogs)
    ↓
LLM Triage (Claude Haiku) → Keep/Discard
    ↓
LLM Signal Extraction (Claude Sonnet) → Structured insights
    ↓
Local Summarization (LexRank) → 3-8 sentence summaries
    ↓
PostgreSQL Database → Queryable storage
```

See [docs/architecture.md](docs/architecture.md) for detailed design.

## Tech Stack

- **Python 3.13** + **uv** - Fast dependency management
- **Docker** + **Docker Compose** - Container orchestration
- **PostgreSQL 16** - State storage
- **LiteLLM** - Multi-provider LLM abstraction
- **Claude (Anthropic)** - Haiku for triage, Sonnet for extraction
- **sumy** - Local extractive summarization
- **trafilatura/newspaper3k** - Content extraction
- **pdfplumber** - PDF text extraction

## CLI Usage

```bash
# All commands run inside Docker container

# Check status
docker exec pydigestor-app uv run pydigestor status

# Show configuration
docker exec pydigestor-app uv run pydigestor config

# Run pipeline (Phase 1: without LLM)
docker exec pydigestor-app uv run pydigestor ingest

# Run tests
docker exec pydigestor-app uv run pytest

# Run tests with coverage
docker exec pydigestor-app uv run pytest --cov
```

## Development Workflow

```bash
# Start services
cd docker
docker-compose up -d

# View logs
docker-compose logs -f app

# Shell into app container
docker exec -it pydigestor-app bash

# Access database
docker exec -it pydigestor-db psql -U pydigestor -d pydigestor

# Stop services
docker-compose down

# Rebuild after code changes
docker-compose up -d --build
```

## Configuration

Key settings in `.env`:

```bash
# Database (automatically set by docker-compose)
DATABASE_URL=postgresql://pydigestor:pydigestor_dev@db:5432/pydigestor

# LLM (Phase 2 - not yet implemented)
# ANTHROPIC_API_KEY=sk-ant-...
# ENABLE_TRIAGE=true
# ENABLE_EXTRACTION=true

# Feeds
RSS_FEEDS=["https://krebsonsecurity.com/feed/"]
REDDIT_SUBREDDITS=["netsec"]

# Summarization
SUMMARIZATION_METHOD=lexrank
```

See [docs/feed sources.md](docs/feed%20sources.md) for recommended feeds.

## Project Structure

```
pyDigestor/
├── docker/
│   ├── Dockerfile              # App container
│   ├── docker-compose.yml      # Multi-container setup
│   └── entrypoint.sh           # Container startup script
├── src/pydigestor/             # Main application code
│   ├── cli.py                  # CLI interface
│   ├── config.py               # Configuration
│   ├── database.py             # Database connection
│   ├── models.py               # SQLModel models
│   ├── sources/                # Feed sources
│   ├── steps/                  # Pipeline steps
│   └── utils/                  # Utilities
├── tests/                      # Test suite
├── alembic/                    # Database migrations
├── docs/                       # Documentation
└── pyproject.toml              # Python dependencies
```

## Development Status

**Current phase:** Phase 1 - Core Pipeline (Day 1-2: Project Setup)
**Timeline:** 4 weeks to production
**Status:** ✅ Project structure complete, Docker setup ready

### Phase 1: Core Pipeline (Weeks 1-2)
- [x] Day 1-2: Project setup, Docker, database, models
- [ ] Day 3-4: RSS/Atom feed parsing
- [ ] Day 5: Basic content extraction
- [ ] Day 6-7: Reddit integration
- [ ] Day 8-9: Advanced extraction (PDF, GitHub, patterns)
- [ ] Day 10: Local summarization

See [docs/IMPLEMENTATION_PLAN.md](docs/IMPLEMENTATION_PLAN.md) for complete roadmap.

## Testing

```bash
# Run all tests
docker exec pydigestor-app uv run pytest

# Run with coverage
docker exec pydigestor-app uv run pytest --cov=src/pydigestor --cov-report=html

# Run specific test file
docker exec pydigestor-app uv run pytest tests/test_models.py

# Run with verbose output
docker exec pydigestor-app uv run pytest -v -s
```

## Cost Analysis

**Monthly costs (Phase 2):**
- Triage (Haiku): ~$0.05
- Signal extraction (Sonnet): ~$0.37
- **Total: ~$0.42/month**

Local summarization is free (no API calls).

## Documentation

- [docs/IMPLEMENTATION_PLAN.md](docs/IMPLEMENTATION_PLAN.md) - Implementation guide
- [docs/quick start.md](docs/quick%20start.md) - Setup and installation
- [docs/architecture.md](docs/architecture.md) - Technical design
- [docs/local summarization.md](docs/local%20summarization.md) - Summarization guide
- [docs/feed sources.md](docs/feed%20sources.md) - Recommended feeds
- [docs/pattern extraction plan.md](docs/pattern%20extraction%20plan.md) - Content extraction patterns
- [docs/reddit implementation plan updated.md](docs/reddit%20implementation%20plan%20updated.md) - Reddit integration

## License

MIT
