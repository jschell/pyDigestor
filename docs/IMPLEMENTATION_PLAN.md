# pyDigestor Implementation Plan

## Status
**Created**: 2026-01-05
**Current Phase**: Pre-Implementation
**Target Completion**: 4 weeks from start
**Approach**: Option 1 (Sequential Phase 1)

---

## Decision Log

### Architecture Decisions

**AD-001: Docker Strategy**
- **Decision**: Multi-container approach using Docker Compose
- **Rationale**:
  - Separate containers for PostgreSQL and pyDigestor application
  - Better isolation, easier maintenance, follows Docker best practices
  - Can upgrade/restart services independently
  - Postgres container uses official image with persistent volumes
  - App container built from custom Dockerfile with uv
- **Containers**:
  1. `pydigestor-db` - PostgreSQL 16
  2. `pydigestor-app` - Python 3.13 + uv + application code
- **Orchestration**: docker-compose.yml for local development

**AD-002: Package Management**
- **Decision**: Use `uv` inside Docker containers
- **Rationale**: Fast dependency resolution, modern tooling, better than pip
- **Implementation**: Multi-stage Docker build with uv

**AD-003: Testing Strategy**
- **Decision**: Tests from Day 1, TDD approach where practical
- **Rationale**: Catch issues early, enable refactoring confidence
- **Tools**: pytest, pytest-asyncio, pytest-cov

**AD-004: Git Workflow**
- **Decision**: Feature branches with PR workflow
- **Branch naming**: `feature/description`, `fix/description`
- **Main branch**: Protected, requires working tests

**AD-005: API Keys & External Services**
- **Decision**: Local-only processing until explicitly enabled
- **Rationale**: Avoid costs during development, test pipeline without LLM calls
- **Implementation**:
  - Mock/skip triage step (keep all articles)
  - Mock/skip extraction step (generate dummy signals)
  - Focus on feed ingestion, extraction, summarization, storage
- **Phase 2 enablement**: Add real API keys when ready

---

## Project Structure

```
pyDigestor/
├── .github/
│   └── workflows/
│       └── tests.yml           # CI/CD pipeline
├── docs/                       # ✅ Exists
│   ├── architecture.md
│   ├── project summary.md
│   ├── quick start.md
│   ├── reddit implementation plan updated.md
│   ├── pattern extraction plan.md
│   ├── local summarization.md
│   ├── pdf support summary.md
│   ├── feed sources.md
│   ├── readme.md
│   └── IMPLEMENTATION_PLAN.md  # This file
├── src/
│   └── pydigestor/
│       ├── __init__.py
│       ├── cli.py              # Typer CLI interface
│       ├── config.py           # Settings (pydantic-settings)
│       ├── database.py         # SQLModel engine, session
│       ├── models.py           # Database models
│       ├── sources/
│       │   ├── __init__.py
│       │   ├── feeds.py        # RSS/Atom parsing
│       │   ├── reddit.py       # Reddit API integration
│       │   └── extraction.py   # Content extraction (trafilatura, PDF)
│       ├── steps/
│       │   ├── __init__.py
│       │   ├── ingest.py       # Step 1: Fetch feeds
│       │   ├── triage.py       # Step 2: LLM filter (mocked initially)
│       │   ├── extract.py      # Step 3: Signal extraction (mocked)
│       │   └── summarize.py    # Step 4: Local summarization
│       └── utils/
│           ├── __init__.py
│           └── rate_limit.py   # Rate limiter for APIs
├── tests/
│   ├── __init__.py
│   ├── conftest.py             # Pytest fixtures
│   ├── test_config.py
│   ├── test_models.py
│   ├── sources/
│   │   ├── test_feeds.py
│   │   ├── test_reddit.py
│   │   └── test_extraction.py
│   └── steps/
│       ├── test_ingest.py
│       ├── test_triage.py
│       ├── test_extract.py
│       └── test_summarize.py
├── alembic/                    # Database migrations
│   ├── env.py
│   ├── versions/
│   └── alembic.ini
├── docker/
│   ├── Dockerfile              # App container
│   └── docker-compose.yml      # Multi-container orchestration
├── .env.example                # Example environment config
├── .env                        # Local config (gitignored)
├── .gitignore                  # ✅ Exists
├── LICENSE                     # ✅ Exists (MIT)
├── pyproject.toml              # Project metadata, dependencies, uv config
└── README.md                   # Project overview (create from docs/readme.md)
```

---

## Phase 1: Core Pipeline (Weeks 1-2)

### Week 1: Foundation & RSS/Atom

#### **Day 1-2: Project Setup**

**Goals**:
- ✅ Docker environment working
- ✅ Database initialized
- ✅ Project structure in place
- ✅ Tests can run

**Tasks**:
1. Create project structure (directories)
2. Write `pyproject.toml` with dependencies
3. Create `Dockerfile` for app container
4. Create `docker-compose.yml` (db + app)
5. Write `.env.example` and `.env`
6. Set up Alembic for migrations
7. Create initial database schema:
   - `articles` table
   - `triage_decisions` table (placeholder)
   - `signals` table (placeholder)
8. Write basic models in `models.py`
9. Set up pytest configuration
10. Write first test (database connection)

**Deliverables**:
- ✅ `docker-compose up` starts PostgreSQL + app
- ✅ `docker exec pydigestor-app uv run pytest` runs tests
- ✅ Database schema created via Alembic
- ✅ Basic CLI runs: `uv run pydigestor --help`

**Branch**: `feature/project-setup`

**Files to create**:
- `pyproject.toml`
- `docker/Dockerfile`
- `docker/docker-compose.yml`
- `.env.example`
- `src/pydigestor/__init__.py`
- `src/pydigestor/cli.py`
- `src/pydigestor/config.py`
- `src/pydigestor/database.py`
- `src/pydigestor/models.py`
- `alembic/versions/001_initial_schema.py`
- `tests/conftest.py`
- `tests/test_database.py`
- `README.md` (copy from docs/readme.md and adjust)

**Tests**:
```python
# tests/test_database.py
def test_database_connection(db_session):
    """Test database is accessible."""
    assert db_session is not None

# tests/test_models.py
def test_article_model_creation():
    """Test Article model can be created."""
    article = Article(
        source_id="test-123",
        url="https://example.com",
        title="Test Article",
        content="Test content"
    )
    assert article.url == "https://example.com"
```

**Validation**:
- [ ] Docker containers start successfully
- [ ] Database accepts connections
- [ ] Migrations apply cleanly
- [ ] All tests pass
- [ ] CLI shows help text

---

#### **Day 3-4: RSS/Atom Feed Parsing**

**Goals**:
- ✅ Can fetch RSS/Atom feeds
- ✅ Parse entries to common format
- ✅ Store articles in database
- ✅ Handle duplicates

**Tasks**:
1. Implement `FeedEntry` dataclass (common format)
2. Implement `RSSFeedSource` class in `sources/feeds.py`:
   - Use `feedparser` library
   - Fetch feed from URL
   - Parse entries
   - Convert to `FeedEntry` format
   - Handle errors gracefully
3. Implement `IngestStep` in `steps/ingest.py`:
   - Load feed URLs from config
   - Fetch all feeds
   - Check for duplicates (source_id)
   - Insert new articles to database
4. Add CLI command: `uv run pydigestor ingest`
5. Write comprehensive tests:
   - Test feedparser with real feeds
   - Test duplicate detection
   - Test database insertion
   - Mock HTTP for unit tests

**Deliverables**:
- ✅ Can fetch from Krebs feed: `https://krebsonsecurity.com/feed/`
- ✅ Articles stored in database with metadata
- ✅ Duplicate articles skipped
- ✅ Tests cover success and error cases

**Branch**: `feature/rss-feeds`

**Files to create/modify**:
- `src/pydigestor/sources/__init__.py`
- `src/pydigestor/sources/feeds.py`
- `src/pydigestor/steps/ingest.py`
- `tests/sources/test_feeds.py`
- `tests/test_ingest.py`

**Tests**:
```python
# tests/sources/test_feeds.py
def test_fetch_rss_feed():
    """Test fetching real RSS feed."""
    source = RSSFeedSource("https://krebsonsecurity.com/feed/")
    entries = source.fetch()
    assert len(entries) > 0
    assert all(hasattr(e, 'title') for e in entries)

def test_parse_entry_to_common_format():
    """Test converting feedparser entry to FeedEntry."""
    # Mock feedparser entry
    raw_entry = {...}
    entry = FeedEntry.from_feedparser(raw_entry)
    assert entry.title
    assert entry.target_url
    assert entry.published_at

def test_duplicate_detection(db_session):
    """Test articles with same source_id are skipped."""
    # Insert article
    # Try to insert again
    # Assert only one exists
```

**Validation**:
- [ ] `uv run pydigestor ingest` fetches articles
- [ ] Database contains articles from feed
- [ ] Running ingest twice doesn't create duplicates
- [ ] Tests pass with mocked and real feeds

---

#### **Day 5: Basic Content Extraction**

**Goals**:
- ✅ Extract article content from URLs
- ✅ Store full content in database
- ✅ Handle extraction failures gracefully

**Tasks**:
1. Implement `ContentExtractor` in `sources/extraction.py`:
   - Use `trafilatura` as primary method
   - Use `newspaper3k` as fallback
   - Handle timeouts and errors
   - Cache failures to avoid retrying
2. Update `IngestStep` to extract content:
   - For each new article
   - Extract content from target_url
   - Update article with content
3. Add metrics tracking:
   - Extraction success rate
   - Average extraction time
4. Write tests with real URLs and mocks

**Deliverables**:
- ✅ Articles have full content extracted
- ✅ 70%+ extraction success rate
- ✅ Failed extractions logged, don't block pipeline

**Branch**: `feature/content-extraction`

**Files to create/modify**:
- `src/pydigestor/sources/extraction.py`
- `src/pydigestor/steps/ingest.py` (update)
- `tests/sources/test_extraction.py`

**Tests**:
```python
# tests/sources/test_extraction.py
def test_extract_with_trafilatura():
    """Test successful extraction with trafilatura."""
    extractor = ContentExtractor()
    content = extractor.extract("https://example.com/article")
    assert content is not None
    assert len(content) > 200

def test_extraction_fallback():
    """Test fallback to newspaper3k if trafilatura fails."""
    # Mock trafilatura to fail
    # Assert newspaper3k called
    # Assert content extracted

def test_extraction_timeout():
    """Test extraction handles timeouts gracefully."""
    # Mock slow response
    # Assert returns None, doesn't crash

def test_failed_cache():
    """Test failed URLs are cached to avoid retrying."""
    # Extract from bad URL
    # Extract again
    # Assert only tried once
```

**Validation**:
- [ ] End-to-end: Fetch RSS → Extract content → Store to DB
- [ ] Can query database and see full article content
- [ ] Extraction metrics logged
- [ ] Tests pass

---

### Week 2: Reddit & Advanced Extraction

#### **Day 6-7: Reddit API Integration**

**Goals**:
- ✅ Fetch posts from Reddit /new endpoint
- ✅ Parse Reddit JSON to common format
- ✅ Apply recency-based filtering
- ✅ Extract external URLs from posts

**Tasks**:
1. Implement `RateLimiter` in `utils/rate_limit.py`:
   - 30 requests/minute for Reddit
   - Thread-safe
   - Tests with timing
2. Implement `RedditFetcher` in `sources/reddit.py`:
   - Fetch from `/r/{subreddit}/new.json`
   - Handle pagination
   - Apply rate limiting
   - Parse JSON response
3. Implement `QualityFilter` in `sources/reddit.py`:
   - Filter by recency (< 24 hours)
   - Priority scoring (fresher = higher priority)
   - Domain blocking (youtube, twitter, reddit)
   - Skip self-posts with no content
4. Update `IngestStep` to include Reddit:
   - Fetch from configured subreddits
   - Convert to `FeedEntry` format
   - Merge with RSS entries
5. Write comprehensive tests

**Deliverables**:
- ✅ Can fetch fresh posts from r/netsec
- ✅ Posts sorted by priority (freshness)
- ✅ Blocked domains filtered out
- ✅ External URLs extracted correctly

**Branch**: `feature/reddit-integration`

**Files to create/modify**:
- `src/pydigestor/utils/rate_limit.py`
- `src/pydigestor/sources/reddit.py`
- `src/pydigestor/steps/ingest.py` (update)
- `tests/utils/test_rate_limit.py`
- `tests/sources/test_reddit.py`

**Tests**:
```python
# tests/utils/test_rate_limit.py
def test_rate_limiter_enforces_delay():
    """Test rate limiter waits between calls."""
    limiter = RateLimiter(calls_per_minute=60)
    start = time.time()
    limiter.wait_if_needed()
    limiter.wait_if_needed()
    elapsed = time.time() - start
    assert elapsed >= 1.0  # Should wait ~1 second

# tests/sources/test_reddit.py
def test_fetch_subreddit_new():
    """Test fetching /new posts from subreddit."""
    fetcher = RedditFetcher()
    posts = fetcher.fetch_subreddit("netsec", sort="new", limit=10)
    assert len(posts) > 0
    assert all('created_utc' in p for p in posts)

def test_recency_filter():
    """Test filtering posts by age."""
    filter = QualityFilter(max_age_hours=24)

    # Fresh post (2 hours old)
    fresh = {'created_utc': time.time() - 7200, ...}
    assert filter.should_process(fresh) == True

    # Old post (48 hours old)
    old = {'created_utc': time.time() - 172800, ...}
    assert filter.should_process(old) == False

def test_domain_blocking():
    """Test blocked domains are filtered."""
    filter = QualityFilter(blocked_domains=['youtube.com'])
    post = {'url': 'https://youtube.com/watch?v=...', ...}
    assert filter.should_process(post) == False
```

**Validation**:
- [ ] Fetch Reddit posts without rate limit errors
- [ ] Only fresh posts (< 24h) are processed
- [ ] YouTube/Twitter links are blocked
- [ ] Tests pass

---

#### **Day 8-9: Advanced Content Extraction (PDF, GitHub, CVE)**

**Goals**:
- ✅ PDF text extraction working
- ✅ GitHub README extraction
- ✅ CVE database extraction
- ✅ Pattern registry system

**Tasks**:
1. Update `ContentExtractor` with PDF support:
   - Detect PDF via HEAD request and Content-Type
   - Download and extract text with `pdfplumber`
   - Filter short/empty extractions
2. Add GitHub-specific extraction:
   - Extract README content
   - Handle different GitHub URL patterns
3. Add CVE database extraction:
   - nvd.nist.gov patterns
   - cve.mitre.org patterns
   - Combine with post title for context
4. Implement `PatternRegistry`:
   - Register extraction patterns by domain
   - Priority-based matching
   - Metrics tracking per pattern
5. Update tests for all patterns

**Deliverables**:
- ✅ PDF documents extract text locally
- ✅ GitHub repositories extract README
- ✅ CVE pages extract vulnerability info
- ✅ Pattern matching tracks success rates

**Branch**: `feature/pattern-extraction`

**Files to modify**:
- `src/pydigestor/sources/extraction.py` (major update)
- `tests/sources/test_extraction.py` (add pattern tests)

**Tests**:
```python
# tests/sources/test_extraction.py
def test_pdf_detection():
    """Test PDF is detected via Content-Type."""
    extractor = ContentExtractor()
    assert extractor.is_pdf("https://example.com/paper.pdf")

def test_pdf_extraction():
    """Test PDF text extraction."""
    # Use test PDF file
    content = extractor.extract("test_data/sample.pdf")
    assert content is not None
    assert len(content) > 200

def test_github_extraction():
    """Test GitHub README extraction."""
    content = extractor.extract("https://github.com/user/repo")
    assert content is not None
    assert "README" in content or len(content) > 100

def test_pattern_registry():
    """Test pattern matching and priority."""
    registry = PatternRegistry()
    handler = registry.get_handler("https://github.com/user/repo")
    assert handler is not None

def test_extraction_metrics():
    """Test metrics are tracked per pattern."""
    extractor = ContentExtractor()
    extractor.extract("https://github.com/user/repo")
    report = extractor.metrics.report()
    assert "github" in report
```

**Validation**:
- [ ] Can extract text from PDF URLs
- [ ] GitHub projects extract properly
- [ ] CVE pages extract vulnerability details
- [ ] Metrics show pattern performance
- [ ] Tests pass

---

#### **Day 10: Local Summarization**

**Goals**:
- ✅ Generate extractive summaries locally
- ✅ Adaptive sentence count (3-8 sentences)
- ✅ Store summaries in database
- ✅ No LLM API calls

**Tasks**:
1. Implement `AdaptiveSummarizer` in `steps/summarize.py`:
   - Use `sumy` library (LexRank)
   - Calculate optimal sentence count (sqrt formula)
   - Handle edge cases (too short, empty)
2. Implement `SummarizeStep`:
   - Query articles without summaries
   - Generate summary for each
   - Update database
3. Add CLI command: `uv run pydigestor summarize`
4. Write tests

**Deliverables**:
- ✅ All articles have summaries
- ✅ Summaries are 3-8 sentences
- ✅ Summarization fast (< 2 sec/article)
- ✅ Free (no API costs)

**Branch**: `feature/local-summarization`

**Files to create**:
- `src/pydigestor/steps/summarize.py`
- `tests/steps/test_summarize.py`

**Tests**:
```python
# tests/steps/test_summarize.py
def test_adaptive_sentence_count():
    """Test adaptive sentence count calculation."""
    summarizer = AdaptiveSummarizer()

    # Short text (10 sentences) → 3 sentences
    short = "Sentence. " * 10
    summary = summarizer.summarize(short)
    assert len(sent_tokenize(summary)) == 3

    # Long text (100 sentences) → 8 sentences
    long = "Sentence. " * 100
    summary = summarizer.summarize(long)
    assert len(sent_tokenize(summary)) == 8

def test_summarize_step(db_session):
    """Test summarize step updates database."""
    # Insert article without summary
    article = Article(url="...", content="..." * 50)
    db_session.add(article)
    db_session.commit()

    # Run summarize step
    step = SummarizeStep()
    step.run()

    # Check summary added
    db_session.refresh(article)
    assert article.summary is not None
```

**Validation**:
- [ ] `uv run pydigestor summarize` generates summaries
- [ ] Database articles have summary field populated
- [ ] Summaries are concise and coherent
- [ ] Tests pass

---

### Week 2 Deliverables

By end of Week 2:
- ✅ **Phase 1 Complete**: Core pipeline functional
- ✅ Can fetch RSS/Atom feeds
- ✅ Can fetch Reddit posts (r/netsec, r/blueteamsec)
- ✅ Can extract content (articles, PDFs, GitHub, CVE)
- ✅ Can generate local summaries
- ✅ All data stored in PostgreSQL
- ✅ CLI commands work
- ✅ Tests pass
- ✅ Docker containers running

**Success Criteria**:
- [ ] End-to-end test: Fetch → Extract → Summarize → Store
- [ ] 90%+ content extraction success rate
- [ ] All articles have summaries
- [ ] No LLM API calls yet (mocked/skipped)
- [ ] Runs in Docker containers

---

## Phase 2: AI Integration (Week 3)

### Overview

**Goals**:
- Integrate Claude API for triage and extraction
- Mock implementation replaced with real LLM calls
- Cost tracking and monitoring

**Prerequisites**:
- Anthropic API key configured
- Phase 1 complete and stable

### **Day 11-12: Triage Step with Claude Haiku**

**Goals**:
- ✅ LLM-based keep/discard decisions
- ✅ Using Claude Haiku (cheap, fast)
- ✅ 20-30% noise reduction
- ✅ Cost tracking

**Tasks**:
1. Configure LiteLLM in `config.py`
2. Implement `TriageStep` in `steps/triage.py`:
   - Use article summary (not full content)
   - Prompt: "Is this security-relevant? Keep or discard?"
   - Store decision in `triage_decisions` table
   - Mark articles as kept/discarded
3. Add batch processing (40 articles/batch)
4. Track costs per article
5. Write tests with mocked LLM responses

**Deliverables**:
- ✅ Triage decisions stored in database
- ✅ Only "kept" articles proceed to extraction
- ✅ Cost per article tracked (~$0.0001)

**Branch**: `feature/llm-triage`

---

### **Day 13-14: Signal Extraction with Claude Sonnet**

**Goals**:
- ✅ Extract structured signals from articles
- ✅ Using Claude Sonnet (higher quality)
- ✅ Store signals in database
- ✅ Signal types: vulnerability, tool, technique, trend

**Tasks**:
1. Implement `ExtractStep` in `steps/extract.py`:
   - Use article summary
   - Prompt: "Extract security signals..."
   - Parse JSON response
   - Store signals in `signals` table
2. Add retry logic for API failures
3. Track extraction time and cost
4. Write tests

**Deliverables**:
- ✅ Signals extracted and stored
- ✅ Queryable by type
- ✅ Cost per article tracked (~$0.001)

**Branch**: `feature/llm-extraction`

---

### **Day 15: Integration & Testing**

**Goals**:
- ✅ Full pipeline runs end-to-end with LLMs
- ✅ Cost monitoring in place
- ✅ Performance acceptable

**Tasks**:
1. Create `pipeline.py` orchestrator
2. Add `uv run pydigestor run` command (full pipeline)
3. Add cost reporting CLI command
4. Integration tests
5. Performance testing

**Deliverables**:
- ✅ Single command runs entire pipeline
- ✅ Cost tracking works
- ✅ Performance metrics collected

**Branch**: `feature/pipeline-integration`

---

## Phase 3: Polish (Week 4)

### **Day 16-17: CLI & Querying**

**Goals**:
- ✅ Rich CLI interface
- ✅ Query commands
- ✅ Export functionality

**Tasks**:
1. Implement query commands:
   - `pydigestor signals --today`
   - `pydigestor signals --type vulnerability`
   - `pydigestor search "keyword"`
2. Add export commands:
   - `pydigestor export --format json`
   - `pydigestor export --format csv`
3. Add status dashboard:
   - `pydigestor status`
4. Use Rich for formatting

**Branch**: `feature/cli-enhancements`

---

### **Day 18-19: Error Handling & Monitoring**

**Goals**:
- ✅ Graceful error handling
- ✅ Logging and metrics
- ✅ Health checks

**Tasks**:
1. Add structured logging
2. Add retry logic for transient failures
3. Add health check endpoints
4. Error reporting
5. Performance monitoring

**Branch**: `feature/monitoring`

---

### **Day 20: Documentation & Deployment**

**Goals**:
- ✅ Documentation complete
- ✅ Deployment ready
- ✅ Production configuration

**Tasks**:
1. Update README with examples
2. Document deployment process
3. Add docker-compose for production
4. Add systemd timer example
5. Final testing

**Branch**: `feature/documentation`

---

## Testing Strategy

### Test Levels

**Unit Tests** (pytest):
- Individual functions and classes
- Mocked external dependencies
- Fast execution (< 1 second per test)
- Run on every commit

**Integration Tests**:
- Multiple components together
- Real database (test container)
- Mocked external APIs
- Run before merge

**End-to-End Tests**:
- Full pipeline execution
- Docker containers
- Test data fixtures
- Run before release

### Test Coverage Goals

- **Target**: 80% code coverage
- **Critical paths**: 100% coverage (database, extraction, CLI)
- **Nice to have**: 60% coverage (error handling, edge cases)

### Running Tests

```bash
# All tests
docker exec pydigestor-app uv run pytest

# With coverage
docker exec pydigestor-app uv run pytest --cov=src/pydigestor --cov-report=html

# Specific test file
docker exec pydigestor-app uv run pytest tests/test_models.py

# Integration tests only
docker exec pydigestor-app uv run pytest -m integration

# Unit tests only (fast)
docker exec pydigestor-app uv run pytest -m "not integration"
```

---

## Git Workflow

### Branch Strategy

**Main Branch**: `main` (or `master`)
- Protected
- Requires passing tests
- Requires code review (if team)

**Feature Branches**: `feature/description`
- Created from main
- One feature per branch
- Deleted after merge

**Fix Branches**: `fix/description`
- For bug fixes
- Created from main

**Release Branches**: `release/v0.1.0` (future)
- For release preparation

### Commit Messages

Format: `<type>: <description>`

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation
- `test`: Tests
- `refactor`: Code refactoring
- `chore`: Maintenance tasks

Examples:
```
feat: add Reddit API integration
fix: handle PDF extraction timeout
docs: update quick start guide
test: add tests for rate limiter
```

### Pull Request Process

1. Create feature branch
2. Make changes and commit
3. Write/update tests
4. Ensure tests pass
5. Create PR to main
6. Review (if team)
7. Merge and delete branch

---

## Docker Configuration

### Multi-Container Setup

**File**: `docker/docker-compose.yml`

```yaml
version: '3.8'

services:
  db:
    image: postgres:16
    container_name: pydigestor-db
    environment:
      POSTGRES_USER: pydigestor
      POSTGRES_PASSWORD: pydigestor_dev
      POSTGRES_DB: pydigestor
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U pydigestor"]
      interval: 10s
      timeout: 5s
      retries: 5

  app:
    build:
      context: ..
      dockerfile: docker/Dockerfile
    container_name: pydigestor-app
    depends_on:
      db:
        condition: service_healthy
    environment:
      - DATABASE_URL=postgresql://pydigestor:pydigestor_dev@db:5432/pydigestor
    env_file:
      - ../.env
    volumes:
      - ../src:/app/src
      - ../tests:/app/tests
    command: tail -f /dev/null  # Keep container running

volumes:
  pgdata:
```

**File**: `docker/Dockerfile`

```dockerfile
FROM python:3.13-slim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Set working directory
WORKDIR /app

# Copy project files
COPY pyproject.toml .
COPY src ./src
COPY tests ./tests

# Install dependencies
RUN uv sync --frozen

# Run migrations on startup (handled by entrypoint)
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
CMD ["tail", "-f", "/dev/null"]
```

**File**: `docker/entrypoint.sh`

```bash
#!/bin/bash
set -e

# Wait for database
echo "Waiting for database..."
while ! pg_isready -h db -U pydigestor; do
  sleep 1
done

# Run migrations
echo "Running database migrations..."
uv run alembic upgrade head

# Execute command
exec "$@"
```

### Development Workflow

```bash
# Start containers
cd docker
docker-compose up -d

# View logs
docker-compose logs -f app

# Run CLI commands
docker exec pydigestor-app uv run pydigestor --help
docker exec pydigestor-app uv run pydigestor ingest

# Run tests
docker exec pydigestor-app uv run pytest

# Access database
docker exec -it pydigestor-db psql -U pydigestor -d pydigestor

# Stop containers
docker-compose down

# Rebuild after changes
docker-compose up -d --build
```

---

## Configuration Management

### Environment Variables

**File**: `.env.example` (committed to git)
**File**: `.env` (gitignored, local only)

```bash
# Database
DATABASE_URL=postgresql://pydigestor:pydigestor_dev@localhost:5432/pydigestor

# LLM Provider (Phase 2)
# ANTHROPIC_API_KEY=sk-ant-...
# TRIAGE_MODEL=claude-3-haiku-20240307
# EXTRACT_MODEL=claude-3-5-sonnet-20241022

# Feed Sources
RSS_FEEDS=["https://krebsonsecurity.com/feed/","https://www.schneier.com/feed/atom/"]
REDDIT_SUBREDDITS=["netsec","blueteamsec"]
REDDIT_SORT=new
REDDIT_LIMIT=100
REDDIT_MAX_AGE_HOURS=24
REDDIT_MIN_SCORE=0

# Summarization
SUMMARIZATION_METHOD=lexrank
SUMMARY_MIN_SENTENCES=3
SUMMARY_MAX_SENTENCES=8

# Content Extraction
CONTENT_FETCH_TIMEOUT=10
CONTENT_MAX_RETRIES=2
ENABLE_PATTERN_EXTRACTION=true

# Development
LOG_LEVEL=INFO
ENABLE_DEBUG=false
```

### Phase 1 (Local Only) Configuration

```bash
# .env for Phase 1 (no API keys)
DATABASE_URL=postgresql://pydigestor:pydigestor_dev@db:5432/pydigestor

# Skip LLM steps
ENABLE_TRIAGE=false
ENABLE_EXTRACTION=false

# Feeds (start small)
RSS_FEEDS=["https://krebsonsecurity.com/feed/"]
REDDIT_SUBREDDITS=["netsec"]

# Summarization (local only)
SUMMARIZATION_METHOD=lexrank
```

---

## Success Criteria

### Phase 1 Complete
- [ ] Docker containers start successfully
- [ ] Can fetch articles from RSS and Reddit
- [ ] Content extraction works (70%+ success rate)
- [ ] Local summaries generated for all articles
- [ ] All data stored in PostgreSQL
- [ ] CLI commands functional
- [ ] Tests pass (80%+ coverage)
- [ ] No external API costs

### Phase 2 Complete
- [ ] LLM triage working (Claude Haiku)
- [ ] Signal extraction working (Claude Sonnet)
- [ ] Cost tracking accurate
- [ ] Monthly cost < $1
- [ ] Triage reduces articles by 20-30%

### Phase 3 Complete
- [ ] Full pipeline runs reliably
- [ ] Query and export commands work
- [ ] Error handling robust
- [ ] Documentation complete
- [ ] Ready for production deployment

---

## Known Risks & Mitigations

### Risk: External API Rate Limits
- **Mitigation**: Implement rate limiters, respect API guidelines
- **Fallback**: Reduce polling frequency, add backoff logic

### Risk: Content Extraction Failure Rate
- **Mitigation**: Multiple extraction methods, pattern-based fast paths
- **Fallback**: Store failed URLs for manual review

### Risk: Database Performance at Scale
- **Mitigation**: Proper indexes, query optimization
- **Fallback**: Partition tables, archive old data

### Risk: LLM Cost Overruns
- **Mitigation**: Use summaries instead of full content, monitor costs
- **Fallback**: Batch processing, reduce article count

### Risk: Docker Resource Constraints
- **Mitigation**: Resource limits in docker-compose, monitoring
- **Fallback**: Separate containers to different hosts

---

## Future Enhancements (Post-Phase 3)

### Optional Features
- Web dashboard (FastAPI + React)
- Slack/email notifications
- Trend analysis and charts
- More feed sources
- Advanced similarity detection
- Custom signal types
- Search with embeddings
- Real-time processing (webhooks)

### Infrastructure
- Kubernetes deployment
- Multi-region support
- Backup and disaster recovery
- Horizontal scaling
- Monitoring and alerting (Prometheus, Grafana)

---

## Progress Tracking

### Current Status: Pre-Implementation

**Phase 1**: Not started
- Week 1: Not started
- Week 2: Not started

**Phase 2**: Not started

**Phase 3**: Not started

### Next Action

**Start Phase 1, Day 1-2: Project Setup**

Create feature branch and begin implementing:
1. Project structure
2. Docker configuration
3. Database schema
4. Basic models and CLI
5. First tests

**Branch**: `feature/project-setup`

---

## Appendix

### Dependencies (pyproject.toml)

```toml
[project]
name = "pydigestor"
version = "0.1.0"
description = "Feed aggregation and analysis pipeline for security content"
requires-python = ">=3.13"
dependencies = [
    "feedparser>=6.0.10",
    "httpx>=0.25.0",
    "sqlmodel>=0.0.14",
    "alembic>=1.12.0",
    "pydantic-settings>=2.0.0",
    "litellm>=1.0.0",
    "sumy>=0.11.0",
    "nltk>=3.8.0",
    "trafilatura>=1.6.0",
    "newspaper3k>=0.2.8",
    "pdfplumber>=0.10.0",
    "typer>=0.9.0",
    "rich>=13.6.0",
    "pytest>=7.4.0",
    "pytest-asyncio>=0.21.0",
    "pytest-cov>=4.1.0",
    "psycopg2-binary>=2.9.9",
]

[project.scripts]
pydigestor = "pydigestor.cli:app"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_functions = ["test_*"]
markers = [
    "integration: integration tests (slower)",
    "unit: unit tests (fast)",
]

[tool.coverage.run]
source = ["src/pydigestor"]
omit = ["*/tests/*", "*/migrations/*"]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "raise NotImplementedError",
    "if __name__ == .__main__.:",
]
```

### Useful Commands Reference

```bash
# Development
docker-compose up -d                    # Start services
docker-compose logs -f app              # View logs
docker exec pydigestor-app bash         # Shell into app container

# CLI
docker exec pydigestor-app uv run pydigestor --help
docker exec pydigestor-app uv run pydigestor ingest
docker exec pydigestor-app uv run pydigestor summarize
docker exec pydigestor-app uv run pydigestor status

# Testing
docker exec pydigestor-app uv run pytest
docker exec pydigestor-app uv run pytest --cov
docker exec pydigestor-app uv run pytest -v -s

# Database
docker exec -it pydigestor-db psql -U pydigestor -d pydigestor
docker exec pydigestor-app uv run alembic upgrade head
docker exec pydigestor-app uv run alembic revision -m "description"

# Git
git checkout -b feature/project-setup
git add .
git commit -m "feat: initial project setup"
git push -u origin feature/project-setup
```

---

## Document History

- **2026-01-05**: Initial version (Option 1, multi-container Docker, tests from day 1)
