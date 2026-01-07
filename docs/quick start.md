# pyDigestor - Quick Start Guide

## Prerequisites

- **Docker** + **Docker Compose**
- **Git**
- That's it! No Python, database, or API keys required.

## Installation

### 1. Clone Repository

```bash
git clone https://github.com/jschell/pyDigestor.git
cd pyDigestor
```

### 2. Configure Environment

```bash
# Copy example config
cp .env.example .env

# Edit with your preferred RSS feeds (optional)
nano .env
```

**Minimal `.env` (defaults work out of the box):**
```bash
# Database (SQLite file path)
DATABASE_URL=sqlite:///./data/pydigestor.db

# Feed Sources
RSS_FEEDS=["https://krebsonsecurity.com/feed/"]
REDDIT_SUBREDDITS=["netsec"]

# Summarization (local, no API costs)
AUTO_SUMMARIZE=true
SUMMARIZATION_METHOD=lexrank
SUMMARY_MIN_SENTENCES=3
SUMMARY_MAX_SENTENCES=8

# LLM Features (Phase 2 - optional, not required)
ENABLE_TRIAGE=false
ENABLE_EXTRACTION=false
```

### 3. Start Docker Container

```bash
cd docker
docker-compose up -d --build

# Watch logs until migrations complete
docker-compose logs -f
# Wait for: "==> Migrations complete!"
# Press Ctrl+C to stop following logs
```

### 4. Verify Installation

```bash
# Check status
docker exec pydigestor-app uv run pydigestor status

# Expected output:
# pyDigestor Status
# ┌────────────────────┬───────┐
# │ Total Articles     │     0 │
# │   Pending          │     0 │
# │   Processed        │     0 │
# └────────────────────┴───────┘
```

## First Run

### Ingest Articles

```bash
# Run ingestion (fetches feeds, extracts content, summarizes)
docker exec pydigestor-app uv run pydigestor ingest

# Expected output:
# Fetching 27 entries from RSS feeds...
# Auto-summarizing 5 new article(s)...
# ✓ Auto-summarized 5 article(s)
#
# Ingest Results
# ┌───────────────┬───────┐
# │ Total Fetched │    27 │
# │ New Articles  │     5 │
# │ Duplicates    │    22 │
# │ Errors        │     0 │
# └───────────────┴───────┘
```

### Search Articles

```bash
# FTS5 keyword search
docker exec pydigestor-app uv run pydigestor search "CVE"

# Search with limit
docker exec pydigestor-app uv run pydigestor search "ransomware" --limit 5

# Expected output:
# Search Results (3 of 12)
# Query: ransomware
#
# ┌──────────────────────────┬────────────────────────────────┐
# │ Title                    │ Snippet                        │
# ├──────────────────────────┼────────────────────────────────┤
# │ Lockbit Takedown...      │ ...new <mark>ransomware</mark>│
# └──────────────────────────┴────────────────────────────────┘
```

### Build TF-IDF Index (Optional)

```bash
# Build TF-IDF index for ranked search
docker exec pydigestor-app uv run pydigestor build-tfidf-index

# TF-IDF ranked search
docker exec pydigestor-app uv run pydigestor tfidf-search "zero day exploit"

# Expected output:
# TF-IDF Search Results (5 of 27)
# Query: zero day exploit
#
# ┌──────────────────────────┬───────┬──────────────────┐
# │ Title                    │ Score │ Summary          │
# ├──────────────────────────┼───────┼──────────────────┤
# │ New Zero-Day Found...    │ 0.847 │ Researchers...   │
# └──────────────────────────┴───────┴──────────────────┘
```

## CLI Commands

### Basic Operations

```bash
# All commands run inside Docker container

# Check status
docker exec pydigestor-app uv run pydigestor status

# Show configuration
docker exec pydigestor-app uv run pydigestor config

# Ingest articles
docker exec pydigestor-app uv run pydigestor ingest

# Show version
docker exec pydigestor-app uv run pydigestor version
```

### Search Commands

```bash
# FTS5 full-text search
docker exec pydigestor-app uv run pydigestor search "kubernetes security"
docker exec pydigestor-app uv run pydigestor search "CVE-2024" --limit 10

# TF-IDF ranked search
docker exec pydigestor-app uv run pydigestor tfidf-search "machine learning security"
docker exec pydigestor-app uv run pydigestor tfidf-search "ransomware" --min-score 0.2

# Build/rebuild TF-IDF index
docker exec pydigestor-app uv run pydigestor build-tfidf-index --max-features 5000 --min-df 2

# Show top TF-IDF terms
docker exec pydigestor-app uv run pydigestor tfidf-terms --n 20

# Rebuild FTS5 index (if search results inconsistent)
docker exec pydigestor-app uv run pydigestor rebuild-fts-index
```

### Database Commands

```bash
# Access SQLite database directly
docker exec -it pydigestor-app sqlite3 /app/data/pydigestor.db

# List all articles
docker exec pydigestor-app sqlite3 /app/data/pydigestor.db "SELECT id, title, status FROM articles LIMIT 10;"

# Count articles by status
docker exec pydigestor-app sqlite3 /app/data/pydigestor.db "SELECT status, COUNT(*) FROM articles GROUP BY status;"

# Show FTS5 schema
docker exec pydigestor-app sqlite3 /app/data/pydigestor.db "SELECT sql FROM sqlite_master WHERE name='articles_fts';"

# Export database
docker cp pydigestor-app:/app/data/pydigestor.db ./backup.db

# Import database
docker cp ./backup.db pydigestor-app:/app/data/pydigestor.db
```

## Scheduled Execution

### Using Cron

```bash
# Edit crontab on host machine
crontab -e

# Run ingestion every 2 hours
0 */2 * * * docker exec pydigestor-app uv run pydigestor ingest >> /var/log/pydigestor.log 2>&1

# Daily TF-IDF index rebuild (midnight)
0 0 * * * docker exec pydigestor-app uv run pydigestor build-tfidf-index >> /var/log/pydigestor-tfidf.log 2>&1
```

### Using Systemd Timer

**Create service file:**
```bash
sudo nano /etc/systemd/system/pydigestor-ingest.service
```

```ini
[Unit]
Description=pyDigestor Feed Ingestion
After=docker.service
Requires=docker.service

[Service]
Type=oneshot
ExecStart=/usr/bin/docker exec pydigestor-app uv run pydigestor ingest
StandardOutput=journal
StandardError=journal
```

**Create timer file:**
```bash
sudo nano /etc/systemd/system/pydigestor-ingest.timer
```

```ini
[Unit]
Description=Run pyDigestor ingestion every 2 hours

[Timer]
OnBootSec=5min
OnUnitActiveSec=2h
Persistent=true

[Install]
WantedBy=timers.target
```

**Enable and start:**
```bash
sudo systemctl enable pydigestor-ingest.timer
sudo systemctl start pydigestor-ingest.timer

# Check status
sudo systemctl status pydigestor-ingest.timer

# View logs
journalctl -u pydigestor-ingest.service -f
```

## Configuration Options

### Feed Sources

```bash
# RSS/Atom feeds (JSON array)
RSS_FEEDS=["https://krebsonsecurity.com/feed/", "https://www.schneier.com/feed/atom/"]

# Reddit subreddits
REDDIT_SUBREDDITS=["netsec", "blueteamsec"]

# Reddit filters
REDDIT_SORT=new
REDDIT_LIMIT=100
REDDIT_MAX_AGE_HOURS=24
REDDIT_MIN_SCORE=0
REDDIT_PRIORITY_HOURS=6
REDDIT_MIN_COMMENTS=0
REDDIT_BLOCKED_DOMAINS=["youtube.com", "twitter.com", "reddit.com"]
```

See [feed sources.md](feed%20sources.md) for recommended security feeds.

### Summarization

```bash
# Auto-summarize during ingestion
AUTO_SUMMARIZE=true

# Method: lexrank, textrank, or lsa
SUMMARIZATION_METHOD=lexrank

# Sentence count range
SUMMARY_MIN_SENTENCES=3
SUMMARY_MAX_SENTENCES=8

# Target compression ratio (20% of original)
SUMMARY_COMPRESSION_RATIO=0.20

# Minimum content length to summarize
SUMMARY_MIN_CONTENT_LENGTH=200
```

### Content Extraction

```bash
# Enable pattern-based extraction (GitHub, PDFs, arXiv)
ENABLE_PATTERN_EXTRACTION=true

# Fetch timeout (seconds)
CONTENT_FETCH_TIMEOUT=10

# Max retries for failed extractions
CONTENT_MAX_RETRIES=2
```

### LLM Configuration (Optional - Phase 2)

```bash
# Feature flags (disabled by default)
ENABLE_TRIAGE=false
ENABLE_EXTRACTION=false

# API keys (not required for Phase 1)
# ANTHROPIC_API_KEY=sk-ant-...

# Model selection
# TRIAGE_MODEL=claude-3-haiku-20240307
# EXTRACT_MODEL=claude-3-5-sonnet-20241022
```

## Troubleshooting

### Container Won't Start

```bash
# View logs
docker-compose -f docker/docker-compose.yml logs

# Check container status
docker ps -a | grep pydigestor

# Restart container
docker-compose -f docker/docker-compose.yml restart

# Clean rebuild
docker-compose -f docker/docker-compose.yml down
docker-compose -f docker/docker-compose.yml up -d --build
```

### Database Issues

```bash
# Verify database exists
docker exec pydigestor-app ls -lh /app/data/

# Check database integrity
docker exec pydigestor-app sqlite3 /app/data/pydigestor.db "PRAGMA integrity_check;"

# View schema
docker exec pydigestor-app sqlite3 /app/data/pydigestor.db ".schema articles"

# Reset database (DESTRUCTIVE)
docker exec pydigestor-app rm -f /app/data/pydigestor.db
docker-compose -f docker/docker-compose.yml restart
```

### Search Returns No Results

```bash
# Check article count
docker exec pydigestor-app sqlite3 /app/data/pydigestor.db "SELECT COUNT(*) FROM articles;"

# Check FTS index
docker exec pydigestor-app sqlite3 /app/data/pydigestor.db "SELECT COUNT(*) FROM articles_fts;"

# Rebuild FTS index
docker exec pydigestor-app uv run pydigestor rebuild-fts-index

# Test FTS directly
docker exec pydigestor-app sqlite3 /app/data/pydigestor.db "SELECT COUNT(*) FROM articles_fts WHERE articles_fts MATCH 'test';"
```

### No Articles Fetched

```bash
# View configuration
docker exec pydigestor-app uv run pydigestor config

# Test RSS feed manually
curl -v https://krebsonsecurity.com/feed/

# Test Reddit endpoint
curl -H "User-Agent: pyDigestor/1.0" https://www.reddit.com/r/netsec/new.json?limit=5

# Check logs for errors
docker-compose -f docker/docker-compose.yml logs | grep ERROR
```

**Common issues:**
- No new articles (already ingested, check `source_id` deduplication)
- Reddit age filter too strict (increase `REDDIT_MAX_AGE_HOURS`)
- Blocked domains filtering too much (review `REDDIT_BLOCKED_DOMAINS`)

### Summarization Fails

```bash
# Check NLTK data
docker exec pydigestor-app python -c "import nltk; nltk.download('punkt'); nltk.download('stopwords')"

# Disable auto-summarization temporarily
# Set AUTO_SUMMARIZE=false in .env, restart container

# Check content length
docker exec pydigestor-app sqlite3 /app/data/pydigestor.db "SELECT id, LENGTH(content) FROM articles WHERE summary IS NULL LIMIT 10;"
```

## Monitoring

### Container Health

```bash
# Container status
docker ps | grep pydigestor

# Resource usage
docker stats pydigestor-app

# Disk usage
docker exec pydigestor-app df -h /app/data
```

### Database Size

```bash
# Database file size
docker exec pydigestor-app ls -lh /app/data/pydigestor.db

# Table sizes (approximate)
docker exec pydigestor-app sqlite3 /app/data/pydigestor.db "
SELECT
    name,
    (SELECT COUNT(*) FROM articles) as articles_count,
    (SELECT COUNT(*) FROM articles_fts) as fts_count,
    (SELECT COUNT(*) FROM signals) as signals_count
FROM sqlite_master
WHERE type='table' AND name='articles';
"
```

### Logs

```bash
# View container logs
docker-compose -f docker/docker-compose.yml logs -f

# View last 100 lines
docker-compose -f docker/docker-compose.yml logs --tail 100

# Filter for errors
docker-compose -f docker/docker-compose.yml logs | grep -i error
```

## Upgrading

```bash
# Stop container
docker-compose -f docker/docker-compose.yml down

# Pull latest code
git pull origin main

# Rebuild and start
docker-compose -f docker/docker-compose.yml up -d --build

# Verify migrations ran
docker-compose -f docker/docker-compose.yml logs | grep "Migrations complete"
```

## Backup & Restore

### Backup

```bash
# Backup database file
docker cp pydigestor-app:/app/data/pydigestor.db ./backup_$(date +%Y%m%d).db

# Backup TF-IDF index
docker cp pydigestor-app:/app/data/tfidf_index.pkl ./backup_tfidf_$(date +%Y%m%d).pkl

# Backup both with tar
docker exec pydigestor-app tar -czf /tmp/pydigestor_backup.tar.gz /app/data/
docker cp pydigestor-app:/tmp/pydigestor_backup.tar.gz ./backup_$(date +%Y%m%d).tar.gz
```

### Restore

```bash
# Restore database file
docker cp ./backup_20260107.db pydigestor-app:/app/data/pydigestor.db

# Restart container
docker-compose -f docker/docker-compose.yml restart

# Rebuild FTS index (if needed)
docker exec pydigestor-app uv run pydigestor rebuild-fts-index
```

## Development Workflow

### Shell Access

```bash
# Interactive shell in container
docker exec -it pydigestor-app bash

# Run commands inside container
# (no need for docker exec prefix)
uv run pydigestor status
sqlite3 /app/data/pydigestor.db
```

### Live Code Editing

The docker-compose.yml mounts source code as volumes, so you can edit locally:

```bash
# Edit code on host
nano src/pydigestor/cli.py

# Changes are immediately available in container
docker exec pydigestor-app uv run pydigestor version

# For dependency changes, rebuild
docker-compose -f docker/docker-compose.yml up -d --build
```

### Run Tests

```bash
# Run all tests
docker exec pydigestor-app uv run pytest

# Run with coverage
docker exec pydigestor-app uv run pytest --cov=src/pydigestor --cov-report=html

# Run specific test
docker exec pydigestor-app uv run pytest tests/test_models.py -v
```

## Next Steps

1. **Customize feeds** - Edit `.env` with your preferred RSS feeds and subreddits
2. **Schedule ingestion** - Set up cron or systemd timer for automatic updates
3. **Explore search** - Try both FTS5 and TF-IDF search modes
4. **Build TF-IDF index** - Enable ranked search with domain-adaptive vocabulary
5. **Monitor growth** - Track article count and database size

## Common Workflows

### Daily Review

```bash
# Check status
docker exec pydigestor-app uv run pydigestor status

# Ingest new articles
docker exec pydigestor-app uv run pydigestor ingest

# Search for specific topics
docker exec pydigestor-app uv run pydigestor search "CVE vulnerability"
docker exec pydigestor-app uv run pydigestor tfidf-search "zero day"
```

### Weekly Maintenance

```bash
# Rebuild TF-IDF index (as corpus grows)
docker exec pydigestor-app uv run pydigestor build-tfidf-index

# Check top terms
docker exec pydigestor-app uv run pydigestor tfidf-terms --n 20

# Backup database
docker cp pydigestor-app:/app/data/pydigestor.db ./weekly_backup_$(date +%Y%m%d).db
```

### Research Mode

```bash
# Search specific topic
docker exec pydigestor-app uv run pydigestor search "kubernetes security"

# View matching articles in database
docker exec pydigestor-app sqlite3 /app/data/pydigestor.db "
SELECT title, url, summary
FROM articles
WHERE id IN (
    SELECT article_id
    FROM articles_fts
    WHERE articles_fts MATCH 'kubernetes'
);
"
```

## Summary

**Quick start workflow:**
1. `docker-compose up -d --build` - Start container
2. `docker exec pydigestor-app uv run pydigestor ingest` - Fetch articles
3. `docker exec pydigestor-app uv run pydigestor search "CVE"` - Search content
4. Set up cron/systemd for automatic ingestion

**No API keys required** - Everything runs locally

**Zero monthly costs** - SQLite, local summarization, local search

**Support:** See documentation in `docs/` directory or GitHub Issues
