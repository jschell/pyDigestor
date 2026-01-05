# pyDigestor - Architecture

## Core Concept
Automated pipeline that ingests RSS/Atom/Reddit feeds, extracts insights using local and LLM-based processing, and stores structured summaries in a queryable database.

## Design Philosophy
- **State-based processing**: Database is single source of truth
- **Resumable execution**: Each step queries for pending work
- **Local-first summarization**: Use extractive methods before LLM
- **Cost-conscious**: Minimize LLM usage, right-size models
- **Feed-agnostic**: Unified handling of RSS, Atom, and Reddit JSON

## High-Level Flow

```
┌─────────────┐
│   Ingest    │  Fetch feeds (RSS/Atom/Reddit), extract target URLs
└──────┬──────┘
       │
┌──────▼──────┐
│   Triage    │  Fast LLM filter: keep/discard decisions (Haiku)
└──────┬──────┘
       │
┌──────▼──────┐
│   Extract   │  Pull structured insights/signals (Sonnet)
└──────┬──────┘
       │
┌──────▼──────┐
│  Summarize  │  Local extractive summarization (TextRank/LexRank)
└──────┬──────┘
       │
┌──────▼──────┐
│    Store    │  Save to database with metadata
└─────────────┘
```

## Tech Stack

### Core
- **Python 3.13** - Language
- **uv** - Fast dependency management
- **PostgreSQL** - State storage and queries
- **SQLModel** - ORM with Pydantic integration

### Content Processing
- **httpx** - HTTP client for feeds
- **feedparser** - RSS/Atom parsing
- **trafilatura** - Article extraction
- **newspaper3k** - Fallback extraction
- **pdfplumber** - PDF text extraction

### Summarization
- **sumy** - Extractive summarization (TextRank, LexRank, LSA)
- **nltk** - NLP utilities

### AI Layer (Minimal)
- **LiteLLM** - Multi-provider abstraction
- **Claude Haiku** - Triage (cheap, fast)
- **Claude Sonnet** - Signal extraction (quality)

### CLI & Monitoring
- **Typer** - CLI framework
- **Rich** - Terminal formatting
- **Alembic** - Database migrations

## Database Schema

### Core Tables

```sql
-- Raw content from target URLs
CREATE TABLE articles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id TEXT UNIQUE NOT NULL,  -- Deduplication key
    url TEXT NOT NULL,               -- Target URL (actual content)
    title TEXT NOT NULL,
    content TEXT NOT NULL,           -- Full extracted text
    summary TEXT,                    -- Local extractive summary
    published_at TIMESTAMP,
    fetched_at TIMESTAMP DEFAULT NOW(),
    status TEXT DEFAULT 'pending',   -- pending, triaged, processed
    metadata JSONB                   -- Feed source, Reddit score, etc.
);

CREATE INDEX idx_articles_metadata ON articles USING GIN (metadata);

-- Triage decisions
CREATE TABLE triage_decisions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    article_id UUID REFERENCES articles(id),
    keep BOOLEAN NOT NULL,
    reasoning TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Extracted signals/insights
CREATE TABLE signals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    article_id UUID REFERENCES articles(id),
    signal_type TEXT NOT NULL,  -- trend, pain_point, opportunity, etc.
    content TEXT NOT NULL,
    confidence FLOAT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_signals_type ON signals(signal_type);
CREATE INDEX idx_signals_created ON signals(created_at);
```

## Configuration

```bash
# pyDigestor Configuration

# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/pydigestor

# LLM Provider
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...
TRIAGE_MODEL=claude-3-haiku-20240307
EXTRACT_MODEL=claude-3-5-sonnet-20241022

# Feed Sources
RSS_FEEDS=[
    "https://krebsonsecurity.com/feed/",
    "https://www.schneier.com/feed/atom/"
]

REDDIT_SUBREDDITS=["netsec", "blueteamsec"]
REDDIT_MAX_AGE_HOURS=24
REDDIT_BLOCKED_DOMAINS=["youtube.com", "twitter.com", "reddit.com"]

# Summarization
SUMMARIZATION_METHOD=lexrank
SUMMARY_MIN_SENTENCES=3
SUMMARY_MAX_SENTENCES=8

# Content Extraction
ENABLE_PATTERN_EXTRACTION=true
```

## Cost Analysis

**Monthly Costs:**
- Triage: ~$0.05/month
- Extract: ~$0.37/month
- **Total AI: ~$0.42/month**

**Infrastructure:**
- Database: $0 (local) or $15/month (managed)

**Total: $0.42-$15.42/month**