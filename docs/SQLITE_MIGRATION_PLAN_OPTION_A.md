# SQLite Migration Plan - Option A: Clean Slate

**Branch**: `claude/sqlite-vec-investigation-QiSok-4PnWU`
**Date**: 2026-01-07
**Status**: Planning Phase
**Approach**: Clean migration from PostgreSQL to SQLite + FTS5 + sqlite-vec

---

## Executive Summary

**Migration Type**: Clean slate (no data migration)
**Rationale**: Project in dev/POC phase, no production data to preserve
**Goal**: Replace PostgreSQL with SQLite + add hybrid search (FTS5 keyword + sqlite-vec semantic)
**Timeline**: 5 phases, ~3-4 days implementation
**Impact**: Breaking change to database layer, but no API/CLI changes

---

## Current State Analysis

### Existing Infrastructure (PostgreSQL-based)

**Database**: PostgreSQL 16 in Docker container
**ORM**: SQLModel with Pydantic v2
**Migrations**: Alembic with 1 migration (`001_initial_schema.py`)
**Driver**: psycopg2-binary

**Tables**:
- `articles` - UUID primary key, TEXT columns, JSONB metadata
- `triage_decisions` - UUID primary key, foreign key to articles
- `signals` - UUID primary key, foreign key to articles, JSONB metadata

**Containers** (docker-compose.yml):
- `pydigestor-db` (PostgreSQL 16)
- `pydigestor-app` (Python 3.13 + uv)

**Dependencies**:
```toml
"sqlmodel>=0.0.14"
"alembic>=1.12.0"
"psycopg2-binary>=2.9.9"  # PostgreSQL driver
```

### Existing Features (Keep These)

**Content Pipeline**: ✅ Working, keep as-is
- RSS/Atom feed parsing (feedparser)
- Reddit API integration (httpx)
- Content extraction (trafilatura, newspaper3k, pdfplumber)
- Pattern-based extraction (GitHub, CVE, PDF)

**Summarization**: ✅ Working, keep as-is
- NLTK + sumy (LexRank, TextRank, LSA)
- Adaptive sentence count (3-8 sentences)
- Local-only, no LLM calls

**CLI**: ✅ Working, keep interface
- `pydigestor ingest` - fetch feeds
- `pydigestor summarize` - generate summaries
- `pydigestor --help` - show commands

**Tests**: ✅ 106+ passing tests, keep all

### What's Missing (Why SQLite Migration)

**No Search Capability**:
- Cannot search articles by keyword
- Cannot find semantically similar articles
- Cannot rank/filter by relevance

**Database Overhead**:
- Separate PostgreSQL container
- Connection pooling complexity
- Multi-container orchestration

---

## Target State

### New Infrastructure (SQLite-based)

**Database**: Single SQLite file with extensions
**ORM**: SQLModel (unchanged API)
**Migrations**: Alembic (SQLite dialect)
**Driver**: Built-in sqlite3

**Core Tables** (modified):
- `articles` - TEXT primary key (UUID as text), TEXT/JSON columns
- `triage_decisions` - TEXT primary key, TEXT foreign key
- `signals` - TEXT primary key, TEXT foreign key, JSON metadata

**Virtual Tables** (new):
- `articles_fts` - FTS5 full-text index (title, content, summary)
- `article_embeddings` - vec0 vector index (384-dim embeddings)

**Containers** (docker-compose.yml):
- `pydigestor-app` only (no separate DB container)

**Dependencies** (changes):
```toml
# Remove:
- "psycopg2-binary>=2.9.9"

# Add:
+ "sqlite-vec>=0.1.0"
+ "sentence-transformers>=2.2.0"  # for embeddings (local, no API)
```

### New Features (Search Capabilities)

**FTS5 Keyword Search**:
- Full-text search on title, content, summary
- Stemming, ranking, snippet generation
- Query syntax: `"security vulnerability" OR exploit`

**sqlite-vec Semantic Search**:
- Vector embeddings (384-dim, SentenceTransformers)
- Similarity search via cosine distance
- Find conceptually similar articles

**Hybrid Search**:
- Combine FTS5 + vector results
- RRF (Reciprocal Rank Fusion) ranking
- Better relevance than either alone

**CLI Commands** (new):
```bash
pydigestor search "keyword query"           # FTS5 keyword search
pydigestor similar <article-id>             # Vector similarity search
pydigestor hybrid "query"                   # Combined hybrid search
pydigestor reindex                          # Rebuild FTS5/embeddings
```

---

## Integration with IMPLEMENTATION_PLAN.md

### Relationship to Existing Plan

**IMPLEMENTATION_PLAN.md** = Overall project roadmap (3 phases, 4 weeks)
**This document** = Phase 1.5 addendum (SQLite migration + search)

### Where This Fits

**Phase 1** (Weeks 1-2): Core Pipeline
- ✅ Already completed (RSS, Reddit, extraction, summarization)
- ✅ Using PostgreSQL (functional)

**→ Phase 1.5** (Days 1-4): **SQLite Migration + Search** ← THIS PLAN
- Replace PostgreSQL with SQLite
- Add FTS5 keyword search
- Add sqlite-vec semantic search
- Integrate into existing pipeline

**Phase 2** (Week 3): AI Integration
- LLM triage (Claude Haiku)
- Signal extraction (Claude Sonnet)
- Cost tracking
- **No changes needed** - works with SQLite

**Phase 3** (Week 4): Polish
- CLI enhancements
- Query commands
- Error handling
- Documentation

### Updated Timeline

```
┌────────────────────────────────────────────────────────┐
│ IMPLEMENTATION_PLAN.md (Original)                     │
│ Week 1-2: Phase 1 (PostgreSQL)         ✅ DONE        │
│ Week 3:   Phase 2 (AI Integration)     ⏸ PAUSED       │
│ Week 4:   Phase 3 (Polish)             ⏸ PENDING      │
└────────────────────────────────────────────────────────┘
                           ↓
┌────────────────────────────────────────────────────────┐
│ THIS PLAN (SQLite Migration)                          │
│ Day 1-4: Phase 1.5 (SQLite + Search)   ← IN PROGRESS  │
└────────────────────────────────────────────────────────┘
                           ↓
┌────────────────────────────────────────────────────────┐
│ RESUME IMPLEMENTATION_PLAN.md                         │
│ Week 3:   Phase 2 (AI Integration)     ⏭ RESUME       │
│ Week 4:   Phase 3 (Polish)             → CONTINUE      │
└────────────────────────────────────────────────────────┘
```

---

## Phase 1: Database Schema Migration

**Goal**: Replace PostgreSQL with SQLite, maintain data model compatibility
**Duration**: 4-6 hours
**Branch**: Same (`claude/sqlite-vec-investigation-QiSok-4PnWU`)

### Tasks

#### 1.1 Update Configuration (`src/pydigestor/config.py`)

**Change**:
```python
# OLD (PostgreSQL)
database_url: str = Field(
    default="postgresql://pydigestor:pydigestor_dev@localhost:5432/pydigestor",
    description="PostgreSQL connection URL",
)

# NEW (SQLite)
database_url: str = Field(
    default="sqlite:///./data/pydigestor.db",
    description="SQLite database path",
)
```

**Rationale**: SQLite uses file-based storage, no network connection needed

#### 1.2 Update Database Engine (`src/pydigestor/database.py`)

**Changes**:
```python
from sqlmodel import Session, create_engine, event
from sqlite_vec import load as load_sqlite_vec

# Create database engine
engine = create_engine(
    settings.database_url,
    echo=settings.enable_debug,
    connect_args={"check_same_thread": False},  # Allow multi-threaded access
)

# Load sqlite-vec extension on connect
@event.listens_for(engine, "connect")
def on_connect(dbapi_conn, connection_record):
    """Load SQLite extensions on connection."""
    dbapi_conn.enable_load_extension(True)
    load_sqlite_vec(dbapi_conn)
    dbapi_conn.enable_load_extension(False)
```

**Rationale**:
- SQLite requires `check_same_thread=False` for multi-threaded apps
- sqlite-vec must be loaded as extension on each connection

#### 1.3 Update Models (`src/pydigestor/models.py`)

**Changes**:
```python
from uuid import UUID, uuid4
from sqlmodel import Field, SQLModel, Column
from sqlalchemy import Text  # for UUID storage

# UUID as TEXT in SQLite
def uuid_as_str() -> str:
    return str(uuid4())

class Article(SQLModel, table=True):
    __tablename__ = "articles"

    # Change: UUID -> TEXT (store as string)
    id: str = Field(
        default_factory=uuid_as_str,
        primary_key=True,
        sa_column=Column(Text, primary_key=True)
    )
    source_id: str = Field(unique=True, index=True)
    url: str = Field()
    title: str = Field()
    content: str | None = Field(default=None)
    summary: str | None = Field(default=None)
    published_at: datetime | None = Field(default=None)
    fetched_at: datetime = Field(default_factory=datetime.utcnow)
    status: str = Field(default="pending")

    # Change: JSONB -> JSON (SQLite stores as TEXT)
    meta: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(Text)  # JSON as TEXT
    )

# Similar changes for TriageDecision, Signal
```

**Rationale**:
- SQLite doesn't have native UUID type, store as TEXT
- SQLite JSON is stored as TEXT (still queryable via JSON functions)

#### 1.4 Create New Alembic Migration

**File**: `alembic/versions/002_migrate_to_sqlite.py`

```python
"""Migrate to SQLite with FTS5 and sqlite-vec support.

Revision ID: 002
Revises: 001
Create Date: 2026-01-07
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import Text

revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None

def upgrade() -> None:
    """Create SQLite schema with FTS5 and vec0 virtual tables."""

    # Core tables (recreated for SQLite)
    op.create_table(
        'articles',
        sa.Column('id', Text, primary_key=True),
        sa.Column('source_id', Text, nullable=False, unique=True),
        sa.Column('url', Text, nullable=False),
        sa.Column('title', Text, nullable=False),
        sa.Column('content', Text, nullable=True),
        sa.Column('summary', Text, nullable=True),
        sa.Column('published_at', sa.DateTime, nullable=True),
        sa.Column('fetched_at', sa.DateTime, nullable=False),
        sa.Column('status', Text, nullable=False),
        sa.Column('meta', Text, nullable=False),  # JSON as TEXT
    )
    op.create_index('idx_articles_source_id', 'articles', ['source_id'], unique=True)
    op.create_index('idx_articles_status', 'articles', ['status'])
    op.create_index('idx_articles_fetched_at', 'articles', ['fetched_at'])

    # FTS5 virtual table for full-text search
    op.execute("""
        CREATE VIRTUAL TABLE articles_fts USING fts5(
            article_id UNINDEXED,
            title,
            content,
            summary,
            content='',
            tokenize='porter unicode61'
        );
    """)

    # sqlite-vec virtual table for vector embeddings
    op.execute("""
        CREATE VIRTUAL TABLE article_embeddings USING vec0(
            article_id TEXT PRIMARY KEY,
            embedding FLOAT[384]
        );
    """)

    # Triggers to keep FTS5 in sync
    op.execute("""
        CREATE TRIGGER articles_fts_insert AFTER INSERT ON articles
        BEGIN
            INSERT INTO articles_fts(article_id, title, content, summary)
            VALUES (new.id, new.title, COALESCE(new.content, ''), COALESCE(new.summary, ''));
        END;
    """)

    op.execute("""
        CREATE TRIGGER articles_fts_update AFTER UPDATE ON articles
        BEGIN
            DELETE FROM articles_fts WHERE article_id = old.id;
            INSERT INTO articles_fts(article_id, title, content, summary)
            VALUES (new.id, new.title, COALESCE(new.content, ''), COALESCE(new.summary, ''));
        END;
    """)

    op.execute("""
        CREATE TRIGGER articles_fts_delete AFTER DELETE ON articles
        BEGIN
            DELETE FROM articles_fts WHERE article_id = old.id;
        END;
    """)

    # TriageDecision, Signal tables (similar changes)
    # ... (omitted for brevity)

def downgrade() -> None:
    """Not supported - clean slate migration."""
    raise NotImplementedError("Downgrade not supported for clean slate migration")
```

**Rationale**:
- Fresh schema optimized for SQLite
- FTS5 virtual table with porter stemming
- vec0 virtual table for 384-dim embeddings
- Triggers for automatic FTS5 sync

#### 1.5 Update Docker Configuration

**File**: `docker/docker-compose.yml`

```yaml
# Remove entire 'db' service (no PostgreSQL)

services:
  app:
    build:
      context: ..
      dockerfile: docker/Dockerfile
    container_name: pydigestor-app
    # Remove: depends_on (no db service)
    environment:
      - DATABASE_URL=sqlite:////app/data/pydigestor.db
    env_file:
      - ../.env
    volumes:
      - ../src:/app/src
      - ../tests:/app/tests
      - ../alembic:/app/alembic
      - ../data:/app/data  # NEW: SQLite database volume
    command: tail -f /dev/null
    networks:
      - pydigestor-network

volumes:
  # Remove: pgdata
  # Add: data volume for SQLite file (handled by host mount)

networks:
  pydigestor-network:
    driver: bridge
```

**File**: `docker/Dockerfile`

```dockerfile
FROM python:3.13-slim

# Install system dependencies for sqlite-vec
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Copy project files
COPY pyproject.toml uv.lock ./
COPY src ./src
COPY tests ./tests
COPY alembic ./alembic

# Install dependencies (includes sqlite-vec, sentence-transformers)
RUN uv sync --frozen

# Create data directory for SQLite
RUN mkdir -p /app/data

# No entrypoint.sh changes needed (Alembic works with SQLite)
CMD ["tail", "-f", "/dev/null"]
```

**File**: `.env.example`

```bash
# Database (SQLite)
DATABASE_URL=sqlite:///./data/pydigestor.db

# ... rest unchanged ...
```

**Rationale**:
- Single container (no PostgreSQL dependency)
- SQLite file stored in mounted volume for persistence
- Build dependencies for sqlite-vec compilation

#### 1.6 Update Dependencies (`pyproject.toml`)

```toml
dependencies = [
    # ... existing packages ...

    # Remove:
    # "psycopg2-binary>=2.9.9",

    # Add:
    "sqlite-vec>=0.1.0",
    "sentence-transformers>=2.2.0",
]
```

**Rationale**:
- Remove PostgreSQL driver
- Add sqlite-vec for vector search
- Add sentence-transformers for local embeddings (not LLM-based)

### Validation

**Tests**:
```bash
# Database connection works
docker exec pydigestor-app uv run pytest tests/test_database.py

# Models use TEXT UUIDs
docker exec pydigestor-app uv run pytest tests/test_models.py

# Migration applies cleanly
docker exec pydigestor-app uv run alembic upgrade head

# Inspect database
docker exec pydigestor-app sqlite3 /app/data/pydigestor.db ".tables"
# Expected: articles, articles_fts, article_embeddings, triage_decisions, signals
```

**Success Criteria**:
- [ ] Docker builds without PostgreSQL dependency
- [ ] SQLite database created at `/app/data/pydigestor.db`
- [ ] Alembic migration creates all tables + virtual tables
- [ ] sqlite-vec extension loads successfully
- [ ] All existing tests pass (no API changes)

---

## Phase 2: FTS5 Keyword Search

**Goal**: Implement full-text search with FTS5
**Duration**: 3-4 hours

### Tasks

#### 2.1 Create Search Module (`src/pydigestor/search/fts.py`)

```python
"""FTS5 full-text search implementation."""

from dataclasses import dataclass
from sqlmodel import Session
from sqlalchemy import text

@dataclass
class SearchResult:
    """FTS5 search result."""
    article_id: str
    title: str
    snippet: str
    rank: float

class FTS5Search:
    """Full-text search using SQLite FTS5."""

    def search(
        self,
        session: Session,
        query: str,
        limit: int = 10
    ) -> list[SearchResult]:
        """
        Search articles using FTS5.

        Args:
            session: Database session
            query: Search query (FTS5 syntax)
            limit: Max results

        Returns:
            List of ranked search results
        """
        sql = text("""
            SELECT
                fts.article_id,
                articles.title,
                snippet(articles_fts, 1, '<mark>', '</mark>', '...', 40) as snippet,
                fts.rank
            FROM articles_fts fts
            JOIN articles ON articles.id = fts.article_id
            WHERE articles_fts MATCH :query
            ORDER BY rank
            LIMIT :limit
        """)

        results = session.execute(
            sql,
            {"query": query, "limit": limit}
        ).fetchall()

        return [
            SearchResult(
                article_id=row[0],
                title=row[1],
                snippet=row[2],
                rank=row[3]
            )
            for row in results
        ]
```

#### 2.2 Add CLI Command (`src/pydigestor/cli.py`)

```python
import typer
from rich.console import Console
from rich.table import Table
from pydigestor.search.fts import FTS5Search
from pydigestor.database import get_session

app = typer.Typer()
console = Console()

@app.command()
def search(
    query: str,
    limit: int = typer.Option(10, help="Max results"),
):
    """Search articles using keyword search (FTS5)."""
    with next(get_session()) as session:
        searcher = FTS5Search()
        results = searcher.search(session, query, limit)

        if not results:
            console.print(f"[yellow]No results for: {query}[/yellow]")
            return

        table = Table(title=f"Search Results: {query}")
        table.add_column("Title", style="cyan")
        table.add_column("Snippet", style="dim")
        table.add_column("Rank", justify="right")

        for r in results:
            table.add_row(r.title[:50], r.snippet[:80], f"{r.rank:.3f}")

        console.print(table)
```

#### 2.3 Tests (`tests/search/test_fts.py`)

```python
"""Tests for FTS5 search."""

import pytest
from pydigestor.models import Article
from pydigestor.search.fts import FTS5Search

def test_fts5_basic_search(db_session):
    """Test basic FTS5 keyword search."""
    # Insert test articles
    db_session.add(Article(
        source_id="test-1",
        url="https://example.com/1",
        title="SQL Injection Vulnerability",
        content="A critical SQL injection bug was found...",
        summary="SQL injection bug discovered"
    ))
    db_session.add(Article(
        source_id="test-2",
        url="https://example.com/2",
        title="XSS Attack Vector",
        content="Cross-site scripting vulnerabilities...",
        summary="XSS vulnerability in web app"
    ))
    db_session.commit()

    # Search
    searcher = FTS5Search()
    results = searcher.search(db_session, "SQL injection", limit=10)

    # Assertions
    assert len(results) == 1
    assert results[0].title == "SQL Injection Vulnerability"
    assert "SQL injection" in results[0].snippet

def test_fts5_phrase_search(db_session):
    """Test FTS5 phrase search with quotes."""
    # ... (test "exact phrase" matching)

def test_fts5_boolean_search(db_session):
    """Test FTS5 boolean operators (AND, OR, NOT)."""
    # ... (test "vulnerability AND NOT xss")

def test_fts5_stemming(db_session):
    """Test porter stemming works."""
    # Search "vulnerabilities" should match "vulnerability"
    # ...
```

### Validation

**Manual Tests**:
```bash
# Ingest some articles
docker exec pydigestor-app uv run pydigestor ingest

# Search for keywords
docker exec pydigestor-app uv run pydigestor search "vulnerability"
docker exec pydigestor-app uv run pydigestor search "SQL injection"
docker exec pydigestor-app uv run pydigestor search '"zero day"'  # exact phrase
```

**Success Criteria**:
- [ ] FTS5 searches return ranked results
- [ ] Snippet generation works with highlighting
- [ ] Stemming works (search "vulnerabilities", match "vulnerability")
- [ ] Boolean operators work (AND, OR, NOT)
- [ ] Tests pass

---

## Phase 3: sqlite-vec Semantic Search

**Goal**: Add vector embeddings and semantic similarity search
**Duration**: 4-6 hours

### Tasks

#### 3.1 Create Embedding Module (`src/pydigestor/search/embeddings.py`)

```python
"""Embedding generation using SentenceTransformers."""

from sentence_transformers import SentenceTransformer
from functools import lru_cache

@lru_cache(maxsize=1)
def get_embedding_model():
    """Load SentenceTransformer model (cached)."""
    return SentenceTransformer('all-MiniLM-L6-v2')  # 384 dimensions

class EmbeddingGenerator:
    """Generate embeddings for articles."""

    def __init__(self):
        self.model = get_embedding_model()

    def generate(self, text: str) -> list[float]:
        """
        Generate embedding for text.

        Args:
            text: Input text (title + summary)

        Returns:
            384-dimensional embedding vector
        """
        embedding = self.model.encode(text, convert_to_numpy=True)
        return embedding.tolist()

    def generate_for_article(self, article) -> list[float]:
        """Generate embedding for article (title + summary)."""
        text = f"{article.title}. {article.summary or ''}"
        return self.generate(text)
```

#### 3.2 Create Vector Search Module (`src/pydigestor/search/vector.py`)

```python
"""Vector similarity search using sqlite-vec."""

from dataclasses import dataclass
from sqlmodel import Session
from sqlalchemy import text
from pydigestor.search.embeddings import EmbeddingGenerator

@dataclass
class SimilarArticle:
    """Similar article result."""
    article_id: str
    title: str
    summary: str
    distance: float  # cosine distance (lower = more similar)

class VectorSearch:
    """Semantic search using sqlite-vec."""

    def __init__(self):
        self.embedder = EmbeddingGenerator()

    def find_similar(
        self,
        session: Session,
        article_id: str,
        limit: int = 10
    ) -> list[SimilarArticle]:
        """
        Find similar articles using vector similarity.

        Args:
            session: Database session
            article_id: Source article ID
            limit: Max results

        Returns:
            List of similar articles sorted by distance
        """
        # Get source article embedding
        sql = text("SELECT embedding FROM article_embeddings WHERE article_id = :id")
        result = session.execute(sql, {"id": article_id}).fetchone()

        if not result:
            raise ValueError(f"No embedding for article {article_id}")

        source_embedding = result[0]

        # Find similar using vec_distance_cosine
        sql = text("""
            SELECT
                e.article_id,
                a.title,
                a.summary,
                vec_distance_cosine(e.embedding, :source_embedding) as distance
            FROM article_embeddings e
            JOIN articles a ON a.id = e.article_id
            WHERE e.article_id != :source_id
            ORDER BY distance ASC
            LIMIT :limit
        """)

        results = session.execute(
            sql,
            {
                "source_embedding": source_embedding,
                "source_id": article_id,
                "limit": limit
            }
        ).fetchall()

        return [
            SimilarArticle(
                article_id=row[0],
                title=row[1],
                summary=row[2],
                distance=row[3]
            )
            for row in results
        ]

    def search_by_text(
        self,
        session: Session,
        query: str,
        limit: int = 10
    ) -> list[SimilarArticle]:
        """Search by text query (generate embedding on-the-fly)."""
        query_embedding = self.embedder.generate(query)

        sql = text("""
            SELECT
                e.article_id,
                a.title,
                a.summary,
                vec_distance_cosine(e.embedding, :query_embedding) as distance
            FROM article_embeddings e
            JOIN articles a ON a.id = e.article_id
            ORDER BY distance ASC
            LIMIT :limit
        """)

        results = session.execute(
            sql,
            {"query_embedding": query_embedding, "limit": limit}
        ).fetchall()

        return [
            SimilarArticle(
                article_id=row[0],
                title=row[1],
                summary=row[2],
                distance=row[3]
            )
            for row in results
        ]
```

#### 3.3 Integrate into Ingest Pipeline (`src/pydigestor/steps/ingest.py`)

```python
from pydigestor.search.embeddings import EmbeddingGenerator
from sqlalchemy import text

class IngestStep:
    def __init__(self):
        # ... existing init ...
        self.embedder = EmbeddingGenerator()

    def _store_article(self, session: Session, article: Article):
        """Store article and generate embedding."""
        # Add article
        session.add(article)
        session.flush()  # Get article.id

        # Generate embedding if article has title/summary
        if article.title and article.summary:
            embedding = self.embedder.generate_for_article(article)

            # Insert into vec0 table
            sql = text("""
                INSERT INTO article_embeddings (article_id, embedding)
                VALUES (:article_id, :embedding)
            """)
            session.execute(sql, {
                "article_id": article.id,
                "embedding": embedding
            })

        session.commit()
```

**Note**: FTS5 sync happens automatically via triggers

#### 3.4 Add CLI Commands (`src/pydigestor/cli.py`)

```python
@app.command()
def similar(
    article_id: str,
    limit: int = typer.Option(10, help="Max results"),
):
    """Find similar articles using vector similarity."""
    with next(get_session()) as session:
        searcher = VectorSearch()
        results = searcher.find_similar(session, article_id, limit)

        table = Table(title=f"Similar to: {article_id}")
        table.add_column("Title", style="cyan")
        table.add_column("Distance", justify="right")

        for r in results:
            table.add_row(r.title[:60], f"{r.distance:.4f}")

        console.print(table)

@app.command()
def semantic_search(
    query: str,
    limit: int = typer.Option(10, help="Max results"),
):
    """Semantic search using vector embeddings."""
    with next(get_session()) as session:
        searcher = VectorSearch()
        results = searcher.search_by_text(session, query, limit)

        # ... display results ...
```

#### 3.5 Tests (`tests/search/test_vector.py`)

```python
"""Tests for vector search."""

import pytest
from pydigestor.search.embeddings import EmbeddingGenerator
from pydigestor.search.vector import VectorSearch

def test_embedding_generation():
    """Test embedding model works."""
    gen = EmbeddingGenerator()
    embedding = gen.generate("SQL injection vulnerability")

    assert len(embedding) == 384  # MiniLM-L6-v2 dimension
    assert all(isinstance(x, float) for x in embedding)

def test_embedding_similarity():
    """Test similar texts have similar embeddings."""
    gen = EmbeddingGenerator()
    e1 = gen.generate("SQL injection attack")
    e2 = gen.generate("SQL injection vulnerability")
    e3 = gen.generate("machine learning model")

    # Cosine similarity
    def cosine(a, b):
        import numpy as np
        return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

    # e1 and e2 should be more similar than e1 and e3
    assert cosine(e1, e2) > cosine(e1, e3)

def test_vector_search(db_session):
    """Test vector similarity search."""
    # Insert articles with embeddings
    # ... (similar to FTS5 tests)

    # Search
    searcher = VectorSearch()
    results = searcher.search_by_text(db_session, "SQL vulnerability", limit=5)

    # Assertions
    assert len(results) > 0
    assert results[0].distance < 0.5  # reasonable similarity
```

### Validation

**Manual Tests**:
```bash
# Ingest articles (generates embeddings)
docker exec pydigestor-app uv run pydigestor ingest

# Check embeddings were created
docker exec pydigestor-app sqlite3 /app/data/pydigestor.db \
  "SELECT COUNT(*) FROM article_embeddings;"

# Search semantically
docker exec pydigestor-app uv run pydigestor semantic-search "zero day vulnerability"

# Find similar articles
docker exec pydigestor-app uv run pydigestor similar <article-id>
```

**Success Criteria**:
- [ ] Embeddings generated during ingest
- [ ] Vector search returns relevant results
- [ ] Similar articles have low distance scores
- [ ] Model loads and caches properly
- [ ] Tests pass

---

## Phase 4: Hybrid Search (RRF)

**Goal**: Combine FTS5 + vector search with Reciprocal Rank Fusion
**Duration**: 2-3 hours

### Tasks

#### 4.1 Create Hybrid Search Module (`src/pydigestor/search/hybrid.py`)

```python
"""Hybrid search combining FTS5 and vector search."""

from dataclasses import dataclass
from sqlmodel import Session
from pydigestor.search.fts import FTS5Search
from pydigestor.search.vector import VectorSearch

@dataclass
class HybridResult:
    """Hybrid search result."""
    article_id: str
    title: str
    snippet: str
    rrf_score: float
    fts_rank: float | None
    vector_distance: float | None

class HybridSearch:
    """Hybrid search using RRF (Reciprocal Rank Fusion)."""

    def __init__(self, k: int = 60):
        """
        Initialize hybrid search.

        Args:
            k: RRF constant (default 60, from research)
        """
        self.k = k
        self.fts = FTS5Search()
        self.vector = VectorSearch()

    def search(
        self,
        session: Session,
        query: str,
        limit: int = 10,
        fts_weight: float = 0.5,
        vector_weight: float = 0.5,
    ) -> list[HybridResult]:
        """
        Hybrid search with RRF ranking.

        Args:
            session: Database session
            query: Search query
            limit: Max results
            fts_weight: Weight for FTS5 scores (0-1)
            vector_weight: Weight for vector scores (0-1)

        Returns:
            Combined and ranked results
        """
        # Get FTS5 results
        fts_results = self.fts.search(session, query, limit=50)
        fts_ranks = {r.article_id: (i+1, r) for i, r in enumerate(fts_results)}

        # Get vector results
        vector_results = self.vector.search_by_text(session, query, limit=50)
        vector_ranks = {r.article_id: (i+1, r) for i, r in enumerate(vector_results)}

        # Combine with RRF
        all_ids = set(fts_ranks.keys()) | set(vector_ranks.keys())

        scored_results = []
        for article_id in all_ids:
            fts_rank, fts_result = fts_ranks.get(article_id, (None, None))
            vector_rank, vector_result = vector_ranks.get(article_id, (None, None))

            # RRF score: 1/(k + rank)
            fts_score = fts_weight / (self.k + fts_rank) if fts_rank else 0
            vector_score = vector_weight / (self.k + vector_rank) if vector_rank else 0

            rrf_score = fts_score + vector_score

            # Get article details (prefer FTS for snippet)
            if fts_result:
                title = fts_result.title
                snippet = fts_result.snippet
            else:
                title = vector_result.title
                snippet = vector_result.summary[:100]

            scored_results.append(HybridResult(
                article_id=article_id,
                title=title,
                snippet=snippet,
                rrf_score=rrf_score,
                fts_rank=fts_result.rank if fts_result else None,
                vector_distance=vector_result.distance if vector_result else None,
            ))

        # Sort by RRF score descending
        scored_results.sort(key=lambda x: x.rrf_score, reverse=True)

        return scored_results[:limit]
```

#### 4.2 Add CLI Command (`src/pydigestor/cli.py`)

```python
@app.command()
def hybrid(
    query: str,
    limit: int = typer.Option(10, help="Max results"),
):
    """Hybrid search (FTS5 + vector with RRF)."""
    with next(get_session()) as session:
        searcher = HybridSearch()
        results = searcher.search(session, query, limit)

        table = Table(title=f"Hybrid Search: {query}")
        table.add_column("Title", style="cyan")
        table.add_column("RRF Score", justify="right")
        table.add_column("FTS Rank", justify="right")
        table.add_column("Vec Dist", justify="right")

        for r in results:
            table.add_row(
                r.title[:50],
                f"{r.rrf_score:.4f}",
                f"{r.fts_rank:.3f}" if r.fts_rank else "-",
                f"{r.vector_distance:.3f}" if r.vector_distance else "-",
            )

        console.print(table)
```

#### 4.3 Tests (`tests/search/test_hybrid.py`)

```python
"""Tests for hybrid search."""

def test_rrf_calculation():
    """Test RRF score calculation."""
    searcher = HybridSearch(k=60)

    # Rank 1 in both: high score
    # Rank 50 in both: low score
    # Rank 1 in one, missing in other: medium score
    # ... (test RRF math)

def test_hybrid_search(db_session):
    """Test hybrid search combines FTS5 + vector."""
    # Insert diverse articles
    # ... (some keyword matches, some semantic matches)

    # Search
    searcher = HybridSearch()
    results = searcher.search(db_session, "SQL vulnerability", limit=10)

    # Should include both keyword and semantic matches
    assert len(results) > 0
    assert all(r.rrf_score > 0 for r in results)
```

### Validation

**Manual Tests**:
```bash
# Compare search methods
docker exec pydigestor-app uv run pydigestor search "zero day"        # FTS5 only
docker exec pydigestor-app uv run pydigestor semantic-search "zero day"  # Vector only
docker exec pydigestor-app uv run pydigestor hybrid "zero day"        # Combined
```

**Success Criteria**:
- [ ] Hybrid search returns results from both methods
- [ ] RRF scoring ranks results better than either method alone
- [ ] Results include both keyword and semantic matches
- [ ] Tests pass

---

## Phase 5: Integration & Testing

**Goal**: Integrate search into full pipeline, comprehensive testing
**Duration**: 3-4 hours

### Tasks

#### 5.1 Add Reindexing Command

**File**: `src/pydigestor/cli.py`

```python
@app.command()
def reindex(
    force: bool = typer.Option(False, help="Regenerate all embeddings"),
):
    """Rebuild FTS5 index and regenerate embeddings."""
    console.print("[cyan]Reindexing articles...[/cyan]")

    with next(get_session()) as session:
        # Clear FTS5 (triggers will repopulate on next insert)
        session.execute(text("DELETE FROM articles_fts"))

        # Rebuild FTS5
        articles = session.exec(select(Article)).all()
        for article in articles:
            # Triggers handle FTS5, manually handle embeddings
            if article.summary:
                embedder = EmbeddingGenerator()
                embedding = embedder.generate_for_article(article)

                session.execute(text("""
                    INSERT OR REPLACE INTO article_embeddings (article_id, embedding)
                    VALUES (:id, :embedding)
                """), {"id": article.id, "embedding": embedding})

        session.commit()

    console.print("[green]✓ Reindexing complete[/green]")
```

#### 5.2 Update End-to-End Pipeline

**No changes needed** - search is optional, doesn't affect ingestion flow

```bash
# Full pipeline (unchanged)
pydigestor ingest      # Fetch feeds, extract, summarize, auto-generate embeddings
pydigestor summarize   # Generate summaries (if not done in ingest)

# New search commands
pydigestor search "query"           # Keyword search
pydigestor semantic-search "query"  # Semantic search
pydigestor hybrid "query"           # Best of both
pydigestor similar <article-id>     # Find similar
```

#### 5.3 Performance Benchmarks

**File**: `tests/benchmarks/test_search_performance.py`

```python
"""Performance benchmarks for search."""

import pytest
import time

@pytest.mark.benchmark
def test_fts5_latency(db_session, sample_articles):
    """Test FTS5 search latency."""
    searcher = FTS5Search()

    start = time.time()
    results = searcher.search(db_session, "vulnerability", limit=10)
    elapsed = time.time() - start

    assert elapsed < 0.05  # < 50ms for 10k articles
    assert len(results) > 0

@pytest.mark.benchmark
def test_vector_latency(db_session, sample_articles):
    """Test vector search latency."""
    searcher = VectorSearch()

    start = time.time()
    results = searcher.search_by_text(db_session, "vulnerability", limit=10)
    elapsed = time.time() - start

    assert elapsed < 0.1  # < 100ms for 10k articles
    assert len(results) > 0

@pytest.mark.benchmark
def test_hybrid_latency(db_session, sample_articles):
    """Test hybrid search latency."""
    searcher = HybridSearch()

    start = time.time()
    results = searcher.search(db_session, "vulnerability", limit=10)
    elapsed = time.time() - start

    assert elapsed < 0.15  # < 150ms for 10k articles
    assert len(results) > 0
```

#### 5.4 Integration Tests

**File**: `tests/integration/test_full_pipeline.py`

```python
"""End-to-end integration tests."""

def test_full_pipeline_with_search(tmp_path):
    """Test complete pipeline: ingest → summarize → search."""
    # Setup test database
    # ...

    # Ingest
    ingest_step = IngestStep()
    ingest_step.run()

    # Summarize
    summarize_step = SummarizeStep()
    summarize_step.run()

    # Verify search works
    with next(get_session()) as session:
        # FTS5 search
        fts = FTS5Search()
        fts_results = fts.search(session, "test", limit=10)
        assert len(fts_results) > 0

        # Vector search
        vec = VectorSearch()
        vec_results = vec.search_by_text(session, "test", limit=10)
        assert len(vec_results) > 0

        # Hybrid search
        hybrid = HybridSearch()
        hybrid_results = hybrid.search(session, "test", limit=10)
        assert len(hybrid_results) > 0
```

#### 5.5 Update Documentation

**Files to update**:
- `README.md` - Add search commands
- `docs/quick start.md` - Add search examples
- `docs/architecture.md` - Update database section
- `TESTING.md` - Add search test instructions

### Validation

**Full Test Suite**:
```bash
# Unit tests
docker exec pydigestor-app uv run pytest tests/search/

# Integration tests
docker exec pydigestor-app uv run pytest tests/integration/

# All tests (should still pass)
docker exec pydigestor-app uv run pytest

# Benchmarks
docker exec pydigestor-app uv run pytest tests/benchmarks/ -v
```

**Manual E2E Test**:
```bash
# 1. Fresh start
docker-compose down -v
docker-compose up -d --build

# 2. Ingest articles
docker exec pydigestor-app uv run pydigestor ingest

# 3. Verify data
docker exec pydigestor-app sqlite3 /app/data/pydigestor.db "SELECT COUNT(*) FROM articles;"
docker exec pydigestor-app sqlite3 /app/data/pydigestor.db "SELECT COUNT(*) FROM articles_fts;"
docker exec pydigestor-app sqlite3 /app/data/pydigestor.db "SELECT COUNT(*) FROM article_embeddings;"

# 4. Test all search methods
docker exec pydigestor-app uv run pydigestor search "vulnerability"
docker exec pydigestor-app uv run pydigestor semantic-search "zero day exploit"
docker exec pydigestor-app uv run pydigestor hybrid "SQL injection"
```

**Success Criteria**:
- [ ] All 106+ existing tests pass
- [ ] New search tests pass (15+ new tests)
- [ ] Benchmarks meet performance targets
- [ ] End-to-end pipeline works
- [ ] Documentation updated

---

## Rollout Plan

### Step 1: Backup (Optional)

```bash
# Export PostgreSQL data (if desired)
docker exec pydigestor-db pg_dump -U pydigestor pydigestor > backup_$(date +%Y%m%d).sql

# Or just note: we can re-ingest from feeds anytime
```

### Step 2: Branch & Implement

```bash
# Already on correct branch
git branch  # Should show: claude/sqlite-vec-investigation-QiSok-4PnWU

# Implement phases 1-5 (commits as we go)
# ... (implementation work)
```

### Step 3: Testing

```bash
# Run full test suite
docker exec pydigestor-app uv run pytest -v

# Manual smoke tests
docker exec pydigestor-app uv run pydigestor ingest
docker exec pydigestor-app uv run pydigestor search "test"
```

### Step 4: Commit & Push

```bash
git add .
git commit -m "feat: migrate to SQLite with FTS5 and sqlite-vec search"
git push -u origin claude/sqlite-vec-investigation-QiSok-4PnWU
```

### Step 5: Resume IMPLEMENTATION_PLAN.md

After this migration, resume original plan at **Phase 2** (AI Integration):
- Triage step (Claude Haiku) - works with SQLite
- Extraction step (Claude Sonnet) - works with SQLite
- No database changes needed for Phase 2/3

---

## Risk Assessment

### Low Risk ✅

**No production data**: Project in dev/POC phase, can re-ingest feeds anytime
**API compatibility**: SQLModel API unchanged, minimal code changes
**Rollback**: Keep PostgreSQL branch, can revert if needed

### Medium Risk ⚠️

**Embedding generation time**: Initial ingest will be slower (generate embeddings)
**Mitigation**: Generate embeddings async/batch if too slow

**sqlite-vec compilation**: Requires build tools in Docker
**Mitigation**: Test Docker build early, pre-install dependencies

### Risks Mitigated ✅

**UUID compatibility**: Using TEXT storage, works in SQLite
**JSON columns**: SQLite JSON functions work for our use cases
**Test coverage**: Keep all existing tests, add new ones

---

## Success Metrics

### Technical Metrics

- [ ] **Build**: Docker builds without errors
- [ ] **Migrations**: Alembic migration applies cleanly
- [ ] **Tests**: All 106+ tests pass + 15+ new search tests
- [ ] **Performance**: Search latency < targets (50ms FTS5, 100ms vector)
- [ ] **Coverage**: Code coverage maintains 80%+

### Functional Metrics

- [ ] **Search Quality**: Keyword search finds exact matches
- [ ] **Semantic Search**: Vector search finds conceptually similar articles
- [ ] **Hybrid Ranking**: RRF combines results better than either alone
- [ ] **Pipeline**: Ingest → Summarize → Search works end-to-end

### Non-Functional Metrics

- [ ] **Simplicity**: Single container (removed PostgreSQL dependency)
- [ ] **Cost**: Still $0 for storage (was already local PostgreSQL)
- [ ] **Embedding Cost**: Still $0 (local SentenceTransformers, not LLM API)
- [ ] **Deployment**: Easier (single SQLite file vs. PostgreSQL container)

---

## Post-Migration

### Immediate Next Steps

1. **Resume IMPLEMENTATION_PLAN.md Phase 2** (AI Integration):
   - Implement triage step (Claude Haiku)
   - Implement extraction step (Claude Sonnet)
   - Works with SQLite, no changes needed

2. **Optimize Search** (if needed):
   - Add caching for embeddings
   - Batch embedding generation
   - Add search result caching

3. **Documentation**:
   - Update quick start guide
   - Add search examples
   - Document search API

### Future Enhancements

**Phase 3+ (from IMPLEMENTATION_PLAN.md)**:
- CLI enhancements
- Export functionality
- Error handling improvements

**Search Enhancements** (post-Phase 3):
- Web UI for search
- Saved searches
- Search analytics
- Custom ranking weights
- Multilingual search

---

## Appendix

### File Change Summary

**Modified Files** (15):
- `src/pydigestor/config.py` - Update database_url default
- `src/pydigestor/database.py` - Add sqlite-vec loading
- `src/pydigestor/models.py` - UUID as TEXT, JSON as TEXT
- `src/pydigestor/steps/ingest.py` - Add embedding generation
- `src/pydigestor/cli.py` - Add search commands
- `docker/docker-compose.yml` - Remove PostgreSQL service
- `docker/Dockerfile` - Add build dependencies
- `.env.example` - Update DATABASE_URL
- `pyproject.toml` - Update dependencies
- `README.md` - Add search documentation
- `docs/architecture.md` - Update database section
- `docs/quick start.md` - Add search examples
- `TESTING.md` - Add search tests

**New Files** (10):
- `alembic/versions/002_migrate_to_sqlite.py` - Migration
- `src/pydigestor/search/__init__.py`
- `src/pydigestor/search/fts.py` - FTS5 search
- `src/pydigestor/search/vector.py` - Vector search
- `src/pydigestor/search/embeddings.py` - Embedding generation
- `src/pydigestor/search/hybrid.py` - Hybrid search
- `tests/search/test_fts.py` - FTS5 tests
- `tests/search/test_vector.py` - Vector tests
- `tests/search/test_hybrid.py` - Hybrid tests
- `tests/benchmarks/test_search_performance.py` - Performance tests

**Deleted Files** (0):
- None (clean slate, no migration code needed)

### Dependencies Added

```toml
# Remove
- "psycopg2-binary>=2.9.9"

# Add
+ "sqlite-vec>=0.1.0"
+ "sentence-transformers>=2.2.0"
```

**Total Size Impact**: +~200MB (SentenceTransformers model)

### Estimated Timelines

**Phase 1**: 4-6 hours (database migration)
**Phase 2**: 3-4 hours (FTS5 search)
**Phase 3**: 4-6 hours (vector search)
**Phase 4**: 2-3 hours (hybrid search)
**Phase 5**: 3-4 hours (integration & testing)

**Total**: 16-23 hours (~3-4 days of focused work)

---

## Questions & Decisions

### Q1: Embedding Generation Timing

**Options**:
1. **Sync during ingest** - Generate embedding immediately when article is added
2. **Async batch** - Generate embeddings in background job

**Decision**: Option 1 (sync during ingest)
- Simpler implementation
- Ensures search works immediately
- Acceptable performance (< 1 sec/article)
- Can optimize later if needed

### Q2: Vector Dimension

**Options**:
1. **384-dim** (all-MiniLM-L6-v2) - Fast, 80MB model
2. **768-dim** (BERT-base) - Better quality, 400MB model
3. **1536-dim** (OpenAI API) - Best quality, requires API calls

**Decision**: Option 1 (384-dim)
- Local-first (no API costs)
- Fast embedding generation
- Good enough for news articles
- Can upgrade later if needed

### Q3: Search Default

**Options**:
1. Make `search` command use FTS5 (keyword)
2. Make `search` command use hybrid (best)
3. Separate commands for each method

**Decision**: Option 3 (separate commands)
- `search` → FTS5 (fast, keyword)
- `semantic-search` → Vector (semantic)
- `hybrid` → Combined (best relevance)
- Clear intent, user chooses method

---

## References

- **sqlite-vec**: https://github.com/asg017/sqlite-vec
- **FTS5**: https://www.sqlite.org/fts5.html
- **SentenceTransformers**: https://www.sbert.net/
- **RRF Algorithm**: https://plg.uwaterloo.ca/~gvcormac/cormacksigir09-rrf.pdf
- **IMPLEMENTATION_PLAN.md**: Original project plan (PostgreSQL-based)

---

**End of Plan**
