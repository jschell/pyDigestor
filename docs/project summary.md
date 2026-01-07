# pyDigestor - Project Summary

> **ℹ️ NOTE**: This is an early project summary from planning phase. The project has evolved to use SQLite with FTS5 search instead of PostgreSQL. See [../README.md](../README.md) for current status.

## Goal

Build a feed aggregation and analysis pipeline that ingests RSS/Atom/Reddit feeds, extracts security insights, and stores them in a queryable database.

## Core Functionality

**Input:** RSS/Atom feeds + Reddit subreddits
**Processing:** Local summarization + search (FTS5/TF-IDF)
**Output:** SQLite database with FTS5 search of articles and summaries

**Phase 2 (Optional):** LLM-based triage and signal extraction

## Pipeline Steps

1. **Ingest** - Fetch feeds, extract target URLs
2. **Triage** - LLM filter (Claude Haiku)
3. **Extract** - LLM signal extraction (Claude Sonnet)
4. **Summarize** - Local extractive summarization (LexRank)
5. **Store** - Save to database

## Key Design Decisions

### Local-First Summarization
- **Why:** 80% cost savings vs LLM-only approach
- **How:** TextRank/LexRank extractive algorithms
- **Quality:** 70-75% agreement with human summaries

### Pattern-Based Extraction
- **Why:** 3x faster extraction for known sites
- **Patterns:** PDF, GitHub, arXiv, CVE databases, security blogs
- **Fallback:** Generic iterative extraction

### Reddit as Link Aggregator
- **Not a content source:** Extract external URLs from posts
- **Skip self-posts:** Only process external links
- **Metadata preserved:** Store Reddit score, subreddit, permalink

### Unified Feed Interface
- **FeedEntry:** Common structure for RSS, Atom, Reddit
- **Target URL:** Always points to actual content (not Reddit)
- **Feed-agnostic:** Same extraction pipeline for all sources

## Implementation Phases

### Phase 1: Core Pipeline (Week 1-2)
- Feed parsing (RSS + Reddit)
- Content extraction with patterns
- Database storage
- Basic CLI

### Phase 2: AI Integration (Week 3)
- Triage with Haiku
- Signal extraction with Sonnet
- Local summarization integration

### Phase 3: Polish (Week 4)
- Error handling
- Metrics and monitoring
- Documentation
- Testing

**Total: 4 weeks**

## Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Language** | Python 3.13 | Core |
| **Package Manager** | uv | Fast dependency management |
| **Database** | SQLite3 + FTS5 | State storage + full-text search |
| **Search** | scikit-learn | TF-IDF ranked retrieval |
| **ORM** | SQLModel | Database models |
| **LLM Provider** | LiteLLM | Multi-provider abstraction |
| **LLM Models** | Claude Haiku/Sonnet | Triage/extraction |
| **Summarization** | sumy | Local extractive |
| **Feed Parsing** | feedparser | RSS/Atom |
| **Content Extraction** | trafilatura, newspaper3k | Article text |
| **PDF Extraction** | pdfplumber | PDF text |
| **CLI** | Typer + Rich | Interface |

## Cost Structure

**Phase 1 (Current): $0/month**
- All processing is local (no API calls)
- SQLite database (embedded, no hosting costs)
- Summarization via sumy (local)
- Search via FTS5 + TF-IDF (local)

**Phase 2 (Optional LLM): ~$0.42/month**
- Triage (15 articles/day × 30 days × $0.0001): ~$0.05
- Extract (12 articles/day × 30 days × $0.001): ~$0.37
- **Total: ~$0.42/month**

**Infrastructure:**
- Database: $0 (SQLite file-based, no hosting)

**Savings vs original plan:**
- No publishing infrastructure: -$35/month (Ghost)
- No synthesis/selection: -$0.20/month
- No content generation: -$0.40/month
- Local summarization: -$0.20/month
- **Total savings: ~$55/month**

## Target Use Cases

### Daily Security Digest
- Query recent vulnerabilities
- Export for manual review
- Share interesting findings

### Research Database
- Search historical signals
- Track trends over time
- Export for analysis

### Alert System
- High-confidence signals
- Slack notifications
- Email summaries

## Feed Sources

**Reddit:**
- r/netsec (offensive security)
- r/blueteamsec (defensive security)

**RSS:**
- Krebs on Security
- Schneier on Security
- Ars Technica Security
- (Configurable)

**Expected volume:** 30-40 articles/day

## Storage Requirements

**Per article:** ~10 KB  
**Annual:** ~44 MB (12 articles/day × 365 days)  
**5-year:** ~220 MB

Trivial storage requirements.

## Performance

**Daily processing time:** ~70 seconds
- Fetch feeds: 5s
- Extract content: 30s
- Triage: 5s
- Extract signals: 15s
- Summarize: 6s
- Store: <1s

## Query Interface

```bash
# Recent signals
uv run pydigestor signals --today

# By type
uv run pydigestor signals --type vulnerability

# Search
uv run pydigestor search "CVE-2025"

# Export
uv run pydigestor export --format json
```

## What This Is NOT

❌ **Not a content publisher** - No Ghost, no blog, no newsletter  
❌ **Not fully autonomous** - Requires manual review of outputs  
❌ **Not real-time** - Scheduled execution (every 2 hours)  
❌ **Not comprehensive** - Focused on security feeds only

## What This IS

✅ **Feed aggregator** - Collects from multiple sources  
✅ **Signal extractor** - Identifies key insights  
✅ **Local summarizer** - Creates concise summaries  
✅ **Query interface** - Searchable database  
✅ **Cost-optimized** - Minimal LLM usage

## Success Metrics

**Phase 1 (Week 2):**
- ✓ Can fetch and parse 3+ feed types
- ✓ Can extract content from 90%+ of URLs
- ✓ Database stores articles with metadata

**Phase 2 (Week 3):**
- ✓ Triage reduces noise by 20-30%
- ✓ Signal extraction captures key insights
- ✓ Local summarization works for all articles

**Phase 3 (Week 4):**
- ✓ End-to-end pipeline runs reliably
- ✓ CLI provides useful query interface
- ✓ Documentation complete

**Production:**
- ✓ Daily processing < 2 minutes
- ✓ Monthly costs < $1
- ✓ Query response < 1 second

## Future Enhancements

**Optional additions:**
- Web dashboard (FastAPI + React)
- Slack/email notifications
- Trend analysis
- More feed sources
- Advanced similarity detection
- Custom signal types

## Development Workflow

```bash
# Daily development
uv run pytest                    # Run tests
uv run pydigestor run --dry-run # Test pipeline
uv run pydigestor status        # Check results

# Deployment
git push origin main            # Push code
ssh server "cd pyDigestor && git pull && uv sync"
systemctl restart pydigestor    # Restart service
```

## Documentation Structure

```
pyDigestor/
├── README.md                          # Project overview
├── QUICK_START.md                     # Setup guide
├── ARCHITECTURE.md                    # Technical design
├── PROJECT_SUMMARY.md                 # This file
├── docs/
│   ├── LOCAL_SUMMARIZATION.md         # Summarization guide
│   ├── FEED_SOURCES.md                # Recommended feeds
│   ├── PATTERN_EXTRACTION_PLAN.md     # Extraction patterns
│   ├── REDDIT_IMPLEMENTATION_PLAN_UPDATED.md  # Implementation guide
│   └── PDF_SUPPORT_SUMMARY.md         # PDF handling
└── src/
    └── pydigestor/
        ├── sources/
        │   ├── feeds.py               # Feed parsing
        │   └── extraction.py          # Content extraction
        ├── steps/
        │   ├── ingest.py
        │   ├── triage.py
        │   └── extract.py
        ├── models.py                  # Database models
        ├── database.py                # DB connection
        └── cli.py                     # CLI interface
```

## Current Status

**Phase:** Planning → Implementation  
**Next step:** Begin Phase 1 (Feed parsing)  
**Blockers:** None  
**Timeline:** On track for 4-week completion

## Key Contacts

**Project owner:** [Your name]  
**Repository:** https://github.com/youruser/pyDigestor  
**Documentation:** See docs/ directory

## Summary

pyDigestor is a cost-optimized feed aggregation pipeline that:
- Ingests from RSS/Atom/Reddit
- Uses local summarization (80% cost savings)
- Extracts signals with minimal LLM usage
- Stores in queryable PostgreSQL database
- Costs ~$0.42/month to run
- Takes 4 weeks to implement

**Focus:** Ingest and analyze, not publish.