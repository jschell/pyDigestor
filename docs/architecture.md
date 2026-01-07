# pyDigestor - Architecture

## Core Concept
Automated pipeline that ingests RSS/Atom/Reddit feeds, extracts insights using local processing, provides powerful search capabilities via FTS5 and TF-IDF, and stores structured summaries in a lightweight SQLite database.

## Design Philosophy
- **State-based processing**: Database is single source of truth
- **Resumable execution**: Each step queries for pending work
- **Local-first everything**: Summarization, search, and processing (zero API costs)
- **Lightweight deployment**: Single-container SQLite architecture (808MB Docker image)
- **Feed-agnostic**: Unified handling of RSS, Atom, and Reddit JSON
- **Dual search modes**: FTS5 for speed, TF-IDF for ranked relevance

## High-Level Flow

```
┌─────────────┐
│   Ingest    │  Fetch feeds (RSS/Atom/Reddit), extract target URLs
└──────┬──────┘
       │
┌──────▼──────┐
│   Extract   │  Pattern-based extraction (GitHub, PDFs, arXiv)
└──────┬──────┘
       │
┌──────▼──────┐
│  Summarize  │  Local extractive summarization (LexRank/TextRank/LSA)
└──────┬──────┘
       │
┌──────▼──────┐
│    Store    │  Save to SQLite with automatic FTS5 indexing
└──────┬──────┘
       │
┌──────▼──────┐
│   Search    │  FTS5 keyword search + TF-IDF ranked retrieval
└─────────────┘
```

**Optional LLM Pipeline (Phase 2):**
```
Articles → Triage (Haiku) → Keep/Discard
         → Extract (Sonnet) → Structured insights/signals
```

## Tech Stack

### Core
- **Python 3.13** - Language
- **uv** - Fast dependency management
- **SQLite3** - Lightweight embedded database
- **SQLModel** - ORM with Pydantic integration
- **Alembic** - Database migrations

### Content Processing
- **httpx** - HTTP client for feeds
- **feedparser** - RSS/Atom parsing
- **trafilatura** - Article extraction
- **newspaper3k** - Fallback extraction
- **pdfplumber** - PDF text extraction

### Summarization
- **sumy** - Extractive summarization (TextRank, LexRank, LSA)
- **nltk** - NLP utilities (tokenization, stopwords)

### Search
- **SQLite FTS5** - Full-text search with porter stemming
- **scikit-learn** - TF-IDF vectorization and cosine similarity

### AI Layer (Optional - Phase 2)
- **LiteLLM** - Multi-provider abstraction
- **Claude Haiku** - Triage (cheap, fast)
- **Claude Sonnet** - Signal extraction (quality)

### CLI & Monitoring
- **Typer** - CLI framework
- **Rich** - Terminal formatting

## Database Schema

### Core Tables

```sql
-- Raw content from target URLs
CREATE TABLE articles (
    id TEXT PRIMARY KEY,             -- UUID as TEXT
    source_id TEXT UNIQUE NOT NULL,  -- Deduplication key
    url TEXT NOT NULL,               -- Target URL (actual content)
    title TEXT NOT NULL,
    content TEXT,                    -- Full extracted text
    summary TEXT,                    -- Local extractive summary
    published_at TIMESTAMP,
    fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status TEXT DEFAULT 'pending',   -- pending, processed
    metadata TEXT                    -- JSON metadata
);

CREATE INDEX idx_articles_status ON articles(status);
CREATE INDEX idx_articles_published ON articles(published_at);

-- FTS5 full-text search index (auto-synced via triggers)
CREATE VIRTUAL TABLE articles_fts USING fts5(
    article_id UNINDEXED,
    title,
    content,
    summary,
    tokenize='porter unicode61'
);

-- Triggers to keep FTS5 in sync
CREATE TRIGGER articles_fts_insert AFTER INSERT ON articles
BEGIN
    INSERT INTO articles_fts(article_id, title, content, summary)
    VALUES (new.id, new.title, COALESCE(new.content, ''), COALESCE(new.summary, ''));
END;

CREATE TRIGGER articles_fts_update AFTER UPDATE ON articles
BEGIN
    DELETE FROM articles_fts WHERE article_id = old.id;
    INSERT INTO articles_fts(article_id, title, content, summary)
    VALUES (new.id, new.title, COALESCE(new.content, ''), COALESCE(new.summary, ''));
END;

CREATE TRIGGER articles_fts_delete AFTER DELETE ON articles
BEGIN
    DELETE FROM articles_fts WHERE article_id = old.id;
END;

-- Triage decisions (optional - Phase 2)
CREATE TABLE triage_decisions (
    id TEXT PRIMARY KEY,
    article_id TEXT REFERENCES articles(id),
    keep BOOLEAN NOT NULL,
    reasoning TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Extracted signals/insights (optional - Phase 2)
CREATE TABLE signals (
    id TEXT PRIMARY KEY,
    article_id TEXT REFERENCES articles(id),
    signal_type TEXT NOT NULL,       -- trend, pain_point, opportunity
    content TEXT NOT NULL,
    confidence REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_signals_article_id ON signals(article_id);
CREATE INDEX idx_signals_signal_type ON signals(signal_type);
CREATE INDEX idx_signals_created_at ON signals(created_at);
```

## Search Architecture

### FTS5 Full-Text Search

**Purpose**: Fast keyword search with boolean operators

**Features**:
- Porter stemming for linguistic matching
- Boolean operators (AND, OR, NOT)
- Phrase search with quotes
- Prefix matching
- Automatic indexing via triggers
- Query sanitization for special characters

**Indexing**: Automatic via database triggers on INSERT/UPDATE/DELETE

**Query Example**:
```sql
SELECT articles.id, articles.title,
       snippet(articles_fts, 1, '<mark>', '</mark>', '...', 40) as snippet,
       rank
FROM articles_fts fts
JOIN articles ON articles.id = fts.article_id
WHERE articles_fts MATCH 'kubernetes security'
ORDER BY rank
LIMIT 10;
```

**Performance**: Milliseconds for keyword lookup on 10K+ articles

### TF-IDF Ranked Search

**Purpose**: Domain-adaptive ranked retrieval with relevance scores

**Features**:
- Learns vocabulary from YOUR articles (not generic corpus)
- Cosine similarity ranking (0.0-1.0 scores)
- N-gram phrases (1-3 words) for better phrase matching
- Transparent rankings (inspect which terms matched)
- Optional minimum score threshold

**Indexing**: Manual build via `build-tfidf-index` command
- Creates scikit-learn TfidfVectorizer from all articles
- Stores pickled index in `data/tfidf_index.pkl`
- Rebuild periodically as corpus grows

**Algorithm**:
```python
# Vectorize documents (title weighted 3x + summary + content)
vectorizer = TfidfVectorizer(
    max_features=5000,
    min_df=2,           # Term must appear in 2+ docs
    max_df=0.8,         # Ignore terms in >80% of docs
    ngram_range=(1, 3), # 1-3 word phrases
    stop_words='english',
    sublinear_tf=True
)

# Transform query and compute cosine similarity
query_vector = vectorizer.transform([query])
similarities = cosine_similarity(query_vector, doc_vectors)[0]

# Return top results sorted by similarity score
```

**Performance**: Sub-second for <10K articles, scales to 100K+

**When to use FTS5 vs TF-IDF**:
- **FTS5**: "Find articles mentioning CVE-2024-1234" (exact keyword match)
- **TF-IDF**: "What are the most relevant articles about ransomware trends?" (ranked by relevance)

## Configuration

```bash
# Database (SQLite file path)
DATABASE_URL=sqlite:///./data/pydigestor.db

# LLM Provider (Optional - Phase 2)
# ANTHROPIC_API_KEY=sk-ant-...
# ENABLE_TRIAGE=false
# ENABLE_EXTRACTION=false
# TRIAGE_MODEL=claude-3-haiku-20240307
# EXTRACT_MODEL=claude-3-5-sonnet-20241022

# Feed Sources
RSS_FEEDS=["https://krebsonsecurity.com/feed/"]
REDDIT_SUBREDDITS=["netsec"]

# Reddit Configuration
REDDIT_SORT=new
REDDIT_LIMIT=100
REDDIT_MAX_AGE_HOURS=24
REDDIT_MIN_SCORE=0
REDDIT_BLOCKED_DOMAINS=["youtube.com", "twitter.com", "reddit.com"]

# Summarization (local, no API costs)
AUTO_SUMMARIZE=true
SUMMARIZATION_METHOD=lexrank
SUMMARY_MIN_SENTENCES=3
SUMMARY_MAX_SENTENCES=8
SUMMARY_COMPRESSION_RATIO=0.20

# Content Extraction
CONTENT_FETCH_TIMEOUT=10
CONTENT_MAX_RETRIES=2
ENABLE_PATTERN_EXTRACTION=true
```

## Cost Analysis

**Phase 1 (Current): $0/month**
- All processing is local (no API calls)
- SQLite database (embedded, no hosting)
- Summarization via sumy (local)
- Search via FTS5 + TF-IDF (local)
- **Infrastructure: $0**

**Phase 2 (Optional LLM): ~$0.42/month**
- Triage (Haiku): ~$0.05/month
- Signal extraction (Sonnet): ~$0.37/month
- Based on ~100 articles/month
- **Infrastructure: Still $0 (SQLite)**

**Total: $0-$0.42/month** (vs $15+ for hosted PostgreSQL)

## Deployment Architecture

### Docker Single-Container

```
┌─────────────────────────────────────┐
│  pydigestor-app (808MB)             │
│                                     │
│  ┌─────────────────────────────┐   │
│  │ Python 3.13 + uv            │   │
│  │ - CLI (Typer)               │   │
│  │ - Pipeline Steps            │   │
│  │ - Search (FTS5 + TF-IDF)    │   │
│  │ - Content Extraction        │   │
│  │ - Summarization (sumy)      │   │
│  └─────────────────────────────┘   │
│                                     │
│  ┌─────────────────────────────┐   │
│  │ SQLite Database             │   │
│  │ - /app/data/pydigestor.db   │   │
│  │ - FTS5 indexes              │   │
│  │ - Automatic triggers        │   │
│  └─────────────────────────────┘   │
│                                     │
│  ┌─────────────────────────────┐   │
│  │ TF-IDF Index (pickled)      │   │
│  │ - /app/data/tfidf_index.pkl │   │
│  └─────────────────────────────┘   │
└─────────────────────────────────────┘
         │
         │ Volume Mount
         ▼
  Host: ./data/
  - pydigestor.db
  - tfidf_index.pkl
```

**Advantages**:
- Single container (simple deployment)
- No network overhead (SQLite is in-process)
- Portable database file (easy backup/restore)
- Lightweight (808MB vs 2.5GB with PyTorch)

**Limitations**:
- Not suitable for concurrent writes (single-user tool)
- Database size limited by disk space
- No built-in replication (manual backup required)

## Performance Characteristics

### Ingestion
- **Speed**: ~5-10 articles/second
- **Bottleneck**: Network I/O (fetching content)
- **Optimization**: Parallel HTTP requests with httpx

### Summarization
- **Speed**: ~1-2 seconds per article (local LexRank)
- **Bottleneck**: CPU (sentence tokenization, matrix operations)
- **Optimization**: Skip summarization for short content (<200 chars)

### Search (FTS5)
- **Speed**: <10ms for simple queries on 10K articles
- **Bottleneck**: Result set size, snippet generation
- **Optimization**: LIMIT clause, indexed columns

### Search (TF-IDF)
- **Speed**: ~50-200ms for 10K articles
- **Bottleneck**: Cosine similarity computation
- **Optimization**: Pre-computed doc vectors, sparse matrices

## Security Considerations

### Content Extraction
- **URL validation**: Blocks javascript:, file:, data: schemes
- **Timeout protection**: 10-second fetch timeout
- **Retry limits**: Max 2 retries per article
- **Domain blocking**: Reddit domain blacklist for low-value sites

### Database
- **No network exposure**: SQLite is file-based, no open ports
- **File permissions**: Database file protected by container UID
- **SQL injection**: Parameterized queries via SQLModel ORM

### API Keys (Phase 2)
- **Environment variables**: Never committed to git
- **Docker secrets**: Mounted at runtime via docker-compose env_file
- **Access control**: Keys scoped to minimum required permissions

## Scaling Considerations

**Current architecture scales to:**
- **Articles**: 100K+ (SQLite limit is 281 TB)
- **FTS5 Search**: Sub-second for 100K+ articles
- **TF-IDF Search**: 1-2 seconds for 100K articles
- **Storage**: ~1MB per 100 articles (text-heavy content)

**If you exceed these limits:**
- Migrate to PostgreSQL with pgvector for semantic search
- Implement read replicas for concurrent search queries
- Add Elasticsearch for advanced search features
- Use object storage (S3) for article content
