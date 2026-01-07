# pyDigestor

Feed aggregation and analysis pipeline that ingests RSS/Atom/Reddit feeds, extracts insights using local processing, and provides powerful search capabilities through SQLite FTS5 and TF-IDF ranking.

## Overview

pyDigestor implements a streamlined pipeline:
1. **Ingest** - Fetch feeds (RSS/Atom/Reddit), extract target URLs
2. **Extract** - Content extraction with pattern recognition (GitHub, PDFs, arXiv)
3. **Summarize** - Local extractive summarization (TextRank/LexRank/LSA)
4. **Search** - FTS5 full-text search + TF-IDF ranked retrieval
5. **Store** - SQLite database with automatic FTS indexing

## Key Features

- **Feed-agnostic**: Unified handling of RSS, Atom, and Reddit JSON
- **Local-first processing**: 100% local summarization and search (no API costs)
- **Dual search modes**:
  - FTS5 with porter stemming for fast keyword search
  - TF-IDF domain-adaptive ranked retrieval
- **Pattern-based extraction**: Fast-path for known sites (GitHub, PDFs, arXiv)
- **Lightweight**: Single-container SQLite architecture (808MB Docker image)
- **Security-focused**: Optimized for r/netsec and security content
- **LLM-ready**: Optional Claude integration for triage and extraction (Phase 2)

## Quick Start (Docker)

```bash
# Clone repository
git clone https://github.com/jschell/pyDigestor.git
cd pyDigestor

# Configure environment
cp .env.example .env
# Edit .env with your RSS feeds if needed (defaults to KrebsOnSecurity)

# Start Docker container
cd docker
docker-compose up -d --build

# Wait for migrations to complete
docker-compose logs -f

# Check status
docker exec pydigestor-app uv run pydigestor status

# Ingest articles
docker exec pydigestor-app uv run pydigestor ingest

# Search articles
docker exec pydigestor-app uv run pydigestor search "CVE vulnerability"
```

See [docs/quick start.md](docs/quick%20start.md) for detailed setup instructions.

## Architecture

```
RSS/Atom Feeds + Reddit → Parse → Extract URLs
    ↓
Content Extraction (PDF, GitHub, arXiv, blogs)
    ↓
Pattern-based Extraction → Structured metadata
    ↓
Local Summarization (LexRank) → 3-8 sentence summaries
    ↓
SQLite Database → FTS5 indexed storage
    ↓
Search (FTS5 keyword + TF-IDF ranked)
```

**Optional LLM Pipeline (Phase 2):**
```
Articles → LLM Triage (Claude Haiku) → Keep/Discard
         → LLM Signal Extraction (Claude Sonnet) → Structured insights
```

See [docs/architecture.md](docs/architecture.md) for detailed design.

## Tech Stack

- **Python 3.13** + **uv** - Fast dependency management
- **Docker** + **Docker Compose** - Single-container deployment
- **SQLite3** with **FTS5** - Full-text search with porter stemming
- **scikit-learn** - TF-IDF ranked retrieval
- **sumy** - Local extractive summarization (LexRank, TextRank, LSA)
- **trafilatura/newspaper3k** - Content extraction
- **pdfplumber** - PDF text extraction
- **feedparser** - RSS/Atom parsing
- **LiteLLM** (optional) - Multi-provider LLM abstraction
- **Claude (Anthropic)** (optional) - Triage and extraction

## CLI Usage

### Basic Commands

```bash
# All commands run inside Docker container

# Check status and article counts
docker exec pydigestor-app uv run pydigestor status

# Show configuration (feeds, settings)
docker exec pydigestor-app uv run pydigestor config

# Ingest articles from RSS/Reddit feeds
docker exec pydigestor-app uv run pydigestor ingest

# Show version
docker exec pydigestor-app uv run pydigestor version
```

### Search Commands

```bash
# FTS5 full-text search (fast keyword search)
docker exec pydigestor-app uv run pydigestor search "CVE vulnerability"
docker exec pydigestor-app uv run pydigestor search "ransomware" --limit 5

# TF-IDF ranked search (domain-adaptive)
docker exec pydigestor-app uv run pydigestor tfidf-search "zero day exploit" --limit 10

# Build/rebuild TF-IDF index
docker exec pydigestor-app uv run pydigestor build-tfidf-index --max-features 5000

# Show top TF-IDF terms in your corpus
docker exec pydigestor-app uv run pydigestor tfidf-terms --n 20

# Rebuild FTS5 index (if search results are inconsistent)
docker exec pydigestor-app uv run pydigestor rebuild-fts-index
```

### Database Commands

```bash
# Access SQLite database directly
docker exec pydigestor-app sqlite3 /app/data/pydigestor.db

# List all articles
docker exec pydigestor-app sqlite3 /app/data/pydigestor.db "SELECT id, title, status FROM articles LIMIT 10;"

# Count articles by status
docker exec pydigestor-app sqlite3 /app/data/pydigestor.db "SELECT status, COUNT(*) FROM articles GROUP BY status;"

# Export database
docker cp pydigestor-app:/app/data/pydigestor.db ./backup.db
```

## Search Examples

### FTS5 Full-Text Search

FTS5 provides fast keyword search with porter stemming and boolean operators:

```bash
# Simple keyword search
docker exec pydigestor-app uv run pydigestor search "kubernetes"

# Multiple keywords (implicit AND)
docker exec pydigestor-app uv run pydigestor search "zero day exploit"

# Phrase search
docker exec pydigestor-app uv run pydigestor search '"supply chain attack"'

# Boolean operators
docker exec pydigestor-app uv run pydigestor search "kubernetes OR docker"
docker exec pydigestor-app uv run pydigestor search "security NOT wordpress"
```

**Output:**
```
Search Results (3 of 12)
Query: kubernetes

┏┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
┃┃ Title                        ┃ Snippet
┡╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
││ Critical K8s Vulnerability   │ ...new <mark>Kubernetes</mark> CVE-2024-...
││ Securing Container Workloads │ ...deploy <mark>Kubernetes</mark> security...
││ Cloud Native Security Guide  │ ...<mark>Kubernetes</mark> best practices...
└┴──────────────────────────────┴─────────────────────────────────────────
```

### TF-IDF Ranked Search

TF-IDF provides domain-adaptive ranked search with similarity scores:

```bash
# Build index from your articles (one-time or periodic)
docker exec pydigestor-app uv run pydigestor build-tfidf-index

# Ranked search with scores
docker exec pydigestor-app uv run pydigestor tfidf-search "machine learning security"

# Higher score threshold (more relevant results)
docker exec pydigestor-app uv run pydigestor tfidf-search "ransomware" --min-score 0.2
```

**Output:**
```
TF-IDF Search Results (5 of 27)
Query: ransomware attack

┏┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━
┃┃ Title                        ┃ Score ┃ Summary
┡╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━
││ Lockbit Ransomware Analysis  │ 0.847 │ Detailed analysis of Lockbit...
││ 2024 Ransomware Trends       │ 0.623 │ Annual report on ransomware...
││ Healthcare Security Breach   │ 0.412 │ Hospital systems targeted...
└┴──────────────────────────────┴───────┴────────────────────────────────
```

**TF-IDF Features:**
- Learns vocabulary from YOUR articles (domain-adaptive)
- Ranks by relevance (cosine similarity scores)
- Supports phrase matching (1-3 word n-grams)
- Transparent rankings (can inspect which terms matched)

### View Top Terms

See what terms are most distinctive in your corpus:

```bash
docker exec pydigestor-app uv run pydigestor tfidf-terms --n 20
```

**Output:**
```
Top 20 TF-IDF Terms

┏┳━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━┓
┃┃ Term               ┃ Importance  ┃
┡╇━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━┩
││ zero day           │ 4.23        │
││ cve                │ 3.87        │
││ ransomware         │ 3.45        │
││ kubernetes         │ 2.91        │
││ supply chain       │ 2.78        │
└┴────────────────────┴─────────────┘
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

# Access SQLite database
docker exec -it pydigestor-app sqlite3 /app/data/pydigestor.db

# Stop services
docker-compose down

# Rebuild after code changes
docker-compose up -d --build

# Clean rebuild (removes database)
docker-compose down -v
rm -rf data/pydigestor.db
docker-compose up -d --build
```

## Configuration

Key settings in `.env`:

```bash
# Database (SQLite file path)
DATABASE_URL=sqlite:///./data/pydigestor.db

# LLM (Phase 2 - optional, not yet enabled)
# ANTHROPIC_API_KEY=sk-ant-...
# ENABLE_TRIAGE=false
# ENABLE_EXTRACTION=false

# Feed Sources
RSS_FEEDS=["https://krebsonsecurity.com/feed/"]
REDDIT_SUBREDDITS=["netsec"]

# Reddit Configuration
REDDIT_SORT=new
REDDIT_LIMIT=100
REDDIT_MAX_AGE_HOURS=24
REDDIT_MIN_SCORE=0

# Summarization (local, no API costs)
AUTO_SUMMARIZE=true
SUMMARIZATION_METHOD=lexrank
SUMMARY_MIN_SENTENCES=3
SUMMARY_MAX_SENTENCES=8
```

See [docs/feed sources.md](docs/feed%20sources.md) for recommended feeds.

## Project Structure

```
pyDigestor/
├── docker/
│   ├── Dockerfile              # App container
│   ├── docker-compose.yml      # Container setup
│   └── entrypoint.sh           # Startup script with migrations
├── src/pydigestor/
│   ├── cli.py                  # CLI interface
│   ├── config.py               # Configuration
│   ├── database.py             # SQLite connection
│   ├── models.py               # SQLModel models
│   ├── sources/                # Feed sources (RSS, Reddit)
│   ├── steps/                  # Pipeline steps (ingest, summarize)
│   ├── search/                 # Search implementations (FTS5, TF-IDF)
│   └── utils/                  # Utilities
├── tests/                      # Test suite
├── alembic/                    # Database migrations
├── docs/                       # Documentation
├── data/                       # SQLite database (volume-mounted)
└── pyproject.toml              # Python dependencies
```

## Development Status

**Current phase:** Phase 1 Complete - Core Pipeline with Search
**Status:** ✅ Production-ready for local content aggregation and search

### Completed Features
- ✅ Project setup, Docker, SQLite database
- ✅ RSS/Atom feed parsing
- ✅ Reddit integration with filtering
- ✅ Advanced extraction (PDF, GitHub, arXiv patterns)
- ✅ Local summarization (LexRank/TextRank/LSA)
- ✅ FTS5 full-text search with porter stemming
- ✅ TF-IDF domain-adaptive ranked search
- ✅ Query sanitization and error handling
- ✅ Lightweight architecture (removed PyTorch, 808MB image)

### Phase 2: LLM Integration (Optional)
- [ ] Claude-based triage (Haiku for keep/discard decisions)
- [ ] Signal extraction (Sonnet for structured insights)
- [ ] Cost-optimized LLM usage (~$0.42/month estimated)

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

## Search Architecture

### FTS5 (Fast Keyword Search)

- **Technology**: SQLite FTS5 with porter stemming
- **Indexing**: Automatic via triggers on INSERT/UPDATE/DELETE
- **Query Features**: Boolean operators, phrase search, prefix matching
- **Speed**: Milliseconds for keyword lookup
- **Best for**: Known keywords, CVE numbers, exact phrases

### TF-IDF (Ranked Retrieval)

- **Technology**: scikit-learn TfidfVectorizer with cosine similarity
- **Indexing**: Manual build (one-time or periodic)
- **Query Features**: Relevance ranking, similarity scores, n-gram phrases
- **Speed**: Sub-second for <10K articles
- **Best for**: Exploratory search, topic discovery, ranked results

**When to use which:**
- **FTS5**: "Find articles mentioning CVE-2024-1234"
- **TF-IDF**: "What are the most relevant articles about ransomware trends?"

## Cost Analysis

**Phase 1 (Current): $0/month**
- All processing is local (no API calls)
- SQLite database (no hosting costs)
- Summarization via sumy (local)
- Search via FTS5 + TF-IDF (local)

**Phase 2 (Optional LLM): ~$0.42/month**
- Triage (Haiku): ~$0.05
- Signal extraction (Sonnet): ~$0.37
- Based on ~100 articles/month

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
