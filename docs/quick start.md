# pyDigestor - Quick Start Guide

## Prerequisites

- **Python 3.13+**
- **PostgreSQL 14+**
- **uv** (Python package manager)
- **Anthropic API key**

## Installation

### 1. Clone Repository

```bash
git clone https://github.com/youruser/pyDigestor.git
cd pyDigestor
```

### 2. Install Dependencies

```bash
# Install uv if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install project dependencies
uv sync
```

### 3. Set Up Database

```bash
# Start PostgreSQL (if using Docker)
docker run -d \
  --name pydigestor-db \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=pydigestor \
  -p 5432:5432 \
  postgres:16

# Or use existing PostgreSQL instance
createdb pydigestor
```

### 4. Configure Environment

```bash
# Copy example config
cp .env.example .env

# Edit configuration
nano .env
```

**Minimal `.env`:**
```bash
# Database
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/pydigestor

# LLM Provider
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-your-key-here
TRIAGE_MODEL=claude-3-haiku-20240307
EXTRACT_MODEL=claude-3-5-sonnet-20241022

# Feed Sources
RSS_FEEDS=["https://krebsonsecurity.com/feed/"]
REDDIT_SUBREDDITS=["netsec"]
REDDIT_MAX_AGE_HOURS=24

# Summarization
SUMMARIZATION_METHOD=lexrank
```

### 5. Initialize Database

```bash
# Run migrations
uv run alembic upgrade head

# Verify tables created
uv run python -c "from src.pydigestor.database import engine; print(engine.table_names())"
```

## First Run

### Manual Execution

```bash
# Run full pipeline
uv run pydigestor run

# Expected output:
# ✓ Fetched 15 articles from feeds
# ✓ Triaged 15 articles (12 kept, 3 discarded)
# ✓ Extracted 48 signals from 12 articles
# ✓ Generated 12 summaries
# Pipeline complete in 45 seconds
```

### Check Results

```bash
# View status
uv run pydigestor status

# View recent signals
uv run pydigestor signals --today

# Search articles
uv run pydigestor search "CVE"
```

## Scheduled Execution

### Using Cron

```bash
# Edit crontab
crontab -e

# Add entry (run every 2 hours)
0 */2 * * * cd /path/to/pyDigestor && /home/user/.local/bin/uv run pydigestor run >> /var/log/pydigestor.log 2>&1
```

### Using Systemd Timer

```bash
# Create service file
sudo nano /etc/systemd/system/pydigestor.service
```

```ini
[Unit]
Description=pyDigestor Feed Ingestion
After=postgresql.service

[Service]
Type=oneshot
User=youruser
WorkingDirectory=/path/to/pyDigestor
ExecStart=/home/youruser/.local/bin/uv run pydigestor run
StandardOutput=journal
StandardError=journal
```

```bash
# Create timer
sudo nano /etc/systemd/system/pydigestor.timer
```

```ini
[Unit]
Description=Run pyDigestor every 2 hours

[Timer]
OnBootSec=5min
OnUnitActiveSec=2h

[Install]
WantedBy=timers.target
```

```bash
# Enable and start
sudo systemctl enable pydigestor.timer
sudo systemctl start pydigestor.timer

# Check status
sudo systemctl status pydigestor.timer
```

## CLI Commands

### Pipeline Operations

```bash
# Run full pipeline
uv run pydigestor run

# Run specific step
uv run pydigestor run --step ingest
uv run pydigestor run --step triage
uv run pydigestor run --step extract

# Dry run (no database writes)
uv run pydigestor run --dry-run
```

### Database Management

```bash
# Initialize database
uv run pydigestor db init

# Reset database (DESTRUCTIVE)
uv run pydigestor db reset

# Run migrations
uv run pydigestor db migrate

# Backup database
uv run pydigestor db backup --output backup.sql
```

### Queries

```bash
# Status dashboard
uv run pydigestor status

# Recent signals
uv run pydigestor signals --today
uv run pydigestor signals --last-week

# Filter by type
uv run pydigestor signals --type vulnerability
uv run pydigestor signals --type tool

# Search articles
uv run pydigestor search "lateral movement"

# Export data
uv run pydigestor export --format json --output report.json
uv run pydigestor export --format csv --output signals.csv
```

### Feed Management

```bash
# Test feed
uv run pydigestor feed test --url "https://blog.com/feed/"

# List configured feeds
uv run pydigestor feed list

# Feed statistics
uv run pydigestor feed stats
```

## Configuration Options

### Feed Sources

```bash
# RSS/Atom feeds (array)
RSS_FEEDS=["https://feed1.com/rss", "https://feed2.com/atom"]

# Reddit subreddits (array)
REDDIT_SUBREDDITS=["netsec", "blueteamsec"]

# Reddit filters
REDDIT_MAX_AGE_HOURS=24
REDDIT_BLOCKED_DOMAINS=["youtube.com", "twitter.com"]
```

### Content Extraction

```bash
# Enable pattern-based extraction
ENABLE_PATTERN_EXTRACTION=true

# Extraction timeout
CONTENT_FETCH_TIMEOUT=10

# Max retries
CONTENT_MAX_RETRIES=2
```

### Summarization

```bash
# Method: lexrank, textrank, or lsa
SUMMARIZATION_METHOD=lexrank

# Adaptive sentence count
SUMMARY_MIN_SENTENCES=3
SUMMARY_MAX_SENTENCES=8

# Compression ratio
SUMMARY_COMPRESSION_RATIO=0.20
```

### LLM Configuration

```bash
# Provider (anthropic, openai, etc.)
LLM_PROVIDER=anthropic

# API keys
ANTHROPIC_API_KEY=sk-ant-...
# OPENAI_API_KEY=sk-...

# Model selection
TRIAGE_MODEL=claude-3-haiku-20240307
EXTRACT_MODEL=claude-3-5-sonnet-20241022

# Batch sizes
TRIAGE_BATCH_SIZE=40
EXTRACT_BATCH_SIZE=10
```

## Troubleshooting

### Database Connection Errors

```bash
# Test connection
psql postgresql://postgres:postgres@localhost:5432/pydigestor

# Check PostgreSQL is running
sudo systemctl status postgresql

# Docker container
docker logs pydigestor-db
```

### API Key Issues

```bash
# Test Anthropic API
curl https://api.anthropic.com/v1/messages \
  -H "x-api-key: $ANTHROPIC_API_KEY" \
  -H "anthropic-version: 2023-06-01" \
  -H "content-type: application/json" \
  -d '{"model":"claude-3-haiku-20240307","max_tokens":10,"messages":[{"role":"user","content":"Hi"}]}'
```

### Feed Fetching Errors

```bash
# Test RSS feed manually
curl -v https://krebsonsecurity.com/feed/

# Test Reddit endpoint
curl -H "User-Agent: pyDigestor/1.0" \
     https://www.reddit.com/r/netsec/new.json?limit=5
```

### No Articles Fetched

**Check configuration:**
```bash
# View current config
uv run pydigestor config show

# Verify feeds are reachable
uv run pydigestor feed test-all
```

**Common issues:**
- Feeds return no new content (try older max_age)
- All articles filtered by recency (check REDDIT_MAX_AGE_HOURS)
- Domain blocking too aggressive (check REDDIT_BLOCKED_DOMAINS)

### Summarization Fails

```bash
# Check NLTK data
python -c "import nltk; nltk.download('punkt')"

# Test summarization
uv run pydigestor summarize --test
```

## Monitoring

### Logs

```bash
# View logs (if using systemd)
journalctl -u pydigestor -f

# View cron logs
tail -f /var/log/pydigestor.log
```

### Metrics

```bash
# Pipeline statistics
uv run pydigestor stats

# Example output:
# Articles processed: 450
# Signals extracted: 1,234
# Average triage time: 0.8s
# Average extraction time: 1.2s
# Total cost (30 days): $0.42
```

### Database Size

```sql
-- Check table sizes
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

## Upgrading

```bash
# Pull latest code
git pull origin main

# Update dependencies
uv sync

# Run migrations
uv run alembic upgrade head

# Restart services
sudo systemctl restart pydigestor.timer
```

## Backup & Restore

### Backup

```bash
# Database dump
pg_dump pydigestor > backup_$(date +%Y%m%d).sql

# Or use CLI
uv run pydigestor db backup --output backup.sql
```

### Restore

```bash
# Restore from dump
psql pydigestor < backup_20260103.sql

# Or use CLI
uv run pydigestor db restore --input backup.sql
```

## Next Steps

1. **Add more feeds** - See `docs/FEED_SOURCES.md`
2. **Tune summarization** - Adjust sentence counts
3. **Explore signals** - Query extracted insights
4. **Set up dashboard** - Optional web interface
5. **Export reports** - Generate summaries

## Getting Help

- **Documentation:** `docs/` directory
- **Issues:** GitHub Issues
- **Logs:** Check systemd journal or cron logs
- **Config:** Review `.env` settings

## Common Workflows

### Daily Review

```bash
# Morning routine
uv run pydigestor signals --today --type vulnerability
uv run pydigestor signals --today --type tool

# Export for review
uv run pydigestor export --today --format json > daily.json
```

### Weekly Summary

```bash
# Generate weekly report
uv run pydigestor export --last-week --format csv > weekly.csv

# View statistics
uv run pydigestor stats --week
```

### Research Mode

```bash
# Search specific topic
uv run pydigestor search "kubernetes security"

# Export matching articles
uv run pydigestor export --search "kubernetes" --format json
```

## Summary

**Basic workflow:**
1. Configure feeds and API keys
2. Run `uv run pydigestor run`
3. Query results with `uv run pydigestor signals`
4. Schedule with cron/systemd

**Expected costs:** ~$0.42/month for LLM usage

**Support:** See documentation in `docs/` directory