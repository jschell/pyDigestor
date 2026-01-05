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

## Quick Start

```bash
# Install dependencies
uv sync

# Configure
cp .env.example .env
# Edit .env with your API keys and feed sources

# Initialize database
uv run alembic upgrade head

# Run pipeline
uv run pydigestor run

# View results
uv run pydigestor signals --today
```

See [QUICK_START.md](QUICK_START.md) for detailed setup instructions.

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

See [ARCHITECTURE.md](ARCHITECTURE.md) for detailed design.

## Tech Stack

- **Python 3.13** + **uv** - Fast dependency management
- **PostgreSQL** - State storage
- **LiteLLM** - Multi-provider LLM abstraction
- **Claude (Anthropic)** - Haiku for triage, Sonnet for extraction
- **sumy** - Local extractive summarization
- **trafilatura/newspaper3k** - Content extraction
- **pdfplumber** - PDF text extraction

## CLI Usage

```bash
# Run pipeline
uv run pydigestor run

# Query signals
uv run pydigestor signals --today
uv run pydigestor signals --type vulnerability

# Search
uv run pydigestor search "lateral movement"

# Export
uv run pydigestor export --format json --output report.json

# Status
uv run pydigestor status
```

## Configuration

Key settings in `.env`:

```bash
# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/pydigestor

# LLM
ANTHROPIC_API_KEY=sk-ant-...
TRIAGE_MODEL=claude-3-haiku-20240307
EXTRACT_MODEL=claude-3-5-sonnet-20241022

# Feeds
RSS_FEEDS=["https://krebsonsecurity.com/feed/"]
REDDIT_SUBREDDITS=["netsec", "blueteamsec"]

# Summarization
SUMMARIZATION_METHOD=lexrank
```

See [docs/FEED_SOURCES.md](docs/FEED_SOURCES.md) for recommended feeds.

## Cost Analysis

**Monthly costs:**
- Triage (Haiku): ~$0.05
- Signal extraction (Sonnet): ~$0.37
- **Total: ~$0.42/month**

Local summarization is free (no API calls).

## Documentation

- [QUICK_START.md](QUICK_START.md) - Setup and installation
- [ARCHITECTURE.md](ARCHITECTURE.md) - Technical design
- [docs/LOCAL_SUMMARIZATION.md](docs/LOCAL_SUMMARIZATION.md) - Summarization guide
- [docs/FEED_SOURCES.md](docs/FEED_SOURCES.md) - Recommended feeds
- [docs/PATTERN_EXTRACTION_PLAN.md](docs/PATTERN_EXTRACTION_PLAN.md) - Content extraction patterns
- [docs/REDDIT_IMPLEMENTATION_PLAN_UPDATED.md](docs/REDDIT_IMPLEMENTATION_PLAN_UPDATED.md) - Implementation guide

## Development Status

**Current phase:** Implementation  
**Timeline:** 4 weeks to production

See [PROJECT_SUMMARY.md](PROJECT_SUMMARY.md) for roadmap.

## License

MIT