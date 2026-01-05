# Feed Sources

## Overview

This document lists recommended RSS/Atom feeds and Reddit sources for pyDigestor, focused on security and technology content.

## Reddit Sources (Link Aggregators)

### Security Focused

**r/netsec** - Network Security & Offensive Security
- URL: `https://www.reddit.com/r/netsec/new.json`
- Volume: ~20-30 external links/day
- Quality: High (moderated)
- Content: CVEs, exploits, tools, research

**r/blueteamsec** - Defensive Security & SOC
- URL: `https://www.reddit.com/r/blueteamsec/new.json`
- Volume: ~10-15 external links/day
- Quality: Very high (heavily moderated)
- Content: Detection rules, threat hunting, defensive tools

### Configuration

```bash
REDDIT_SUBREDDITS=["netsec", "blueteamsec"]
```

## RSS/Atom Feeds

### Security News & Analysis

**Krebs on Security**
- URL: `https://krebsonsecurity.com/feed/`
- Author: Brian Krebs
- Focus: Cybercrime, data breaches, investigation
- Update frequency: 2-3 posts/week
- Quality: Investigative journalism, original reporting

**Schneier on Security**
- URL: `https://www.schneier.com/feed/atom/`
- Author: Bruce Schneier
- Focus: Security analysis, cryptography, policy
- Update frequency: Daily
- Quality: Expert analysis and commentary

**Ars Technica - Security**
- URL: `https://feeds.arstechnica.com/arstechnica/security`
- Focus: Security news with technical depth
- Update frequency: Multiple daily
- Quality: Technical journalism

**BleepingComputer - Security**
- URL: `https://www.bleepingcomputer.com/feed/`
- Focus: Malware, ransomware, vulnerabilities
- Update frequency: Multiple daily
- Quality: Fast breaking news

**The Hacker News**
- URL: `https://feeds.feedburner.com/TheHackersNews`
- Focus: Security news and tutorials
- Update frequency: Multiple daily
- Quality: Good coverage of major incidents

### Threat Intelligence

**SANS Internet Storm Center**
- URL: `https://isc.sans.edu/rssfeed.xml`
- Focus: Threat analysis, handlers diary
- Update frequency: Daily
- Quality: Technical analysis from experts

**Malwarebytes Labs**
- URL: `https://blog.malwarebytes.com/feed/`
- Focus: Malware analysis, threat research
- Update frequency: 3-4 posts/week
- Quality: Technical malware research

**Unit 42 (Palo Alto Networks)**
- URL: `https://unit42.paloaltonetworks.com/feed/`
- Focus: Threat research, APT groups
- Update frequency: Weekly
- Quality: In-depth threat intelligence

### Vulnerability & Exploit Research

**Exploit Database**
- URL: `https://www.exploit-db.com/rss.xml`
- Focus: Published exploits, CVEs
- Update frequency: Daily
- Quality: Direct exploit code/PoCs

**Packet Storm Security**
- URL: `https://packetstormsecurity.com/headlines.xml`
- Focus: Exploits, advisories, tools
- Update frequency: Daily
- Quality: Comprehensive security content

### Cloud Security

**AWS Security Blog**
- URL: `https://aws.amazon.com/blogs/security/feed/`
- Focus: AWS security best practices
- Update frequency: Weekly
- Quality: Official vendor guidance

**Google Cloud Security Blog**
- URL: `https://cloud.google.com/blog/products/identity-security/rss`
- Focus: GCP security features
- Update frequency: Monthly
- Quality: Official vendor guidance

### Development & Tools

**GitHub Security Lab**
- URL: `https://securitylab.github.com/rss.xml`
- Focus: Security research, tool development
- Update frequency: Monthly
- Quality: Technical research

## Recommended Starting Configuration

### Minimal Set (High Signal)

```bash
RSS_FEEDS=[
    "https://krebsonsecurity.com/feed/",
    "https://www.schneier.com/feed/atom/",
    "https://feeds.arstechnica.com/arstechnica/security"
]

REDDIT_SUBREDDITS=["netsec", "blueteamsec"]
```

**Expected volume:** ~30-40 articles/day  
**Quality:** Very high  
**Coverage:** News, analysis, research

### Extended Set (Comprehensive)

```bash
RSS_FEEDS=[
    # Core security news
    "https://krebsonsecurity.com/feed/",
    "https://www.schneier.com/feed/atom/",
    "https://feeds.arstechnica.com/arstechnica/security",
    "https://www.bleepingcomputer.com/feed/",
    "https://feeds.feedburner.com/TheHackersNews",
    
    # Threat intelligence
    "https://isc.sans.edu/rssfeed.xml",
    "https://blog.malwarebytes.com/feed/",
    "https://unit42.paloaltonetworks.com/feed/",
    
    # Vulnerabilities
    "https://www.exploit-db.com/rss.xml",
    "https://packetstormsecurity.com/headlines.xml"
]

REDDIT_SUBREDDITS=["netsec", "blueteamsec"]
```

**Expected volume:** ~80-100 articles/day  
**Quality:** High  
**Coverage:** Comprehensive security coverage

## Feed Validation

### Check Feed Status

```bash
# Test RSS feed
curl -I https://krebsonsecurity.com/feed/
# Should return: 200 OK, Content-Type: application/rss+xml

# Test Reddit JSON
curl -H "User-Agent: pyDigestor/1.0" \
     https://www.reddit.com/r/netsec/new.json?limit=5
# Should return: JSON with posts
```

### Validate Feed Format

```python
import feedparser

# Test RSS/Atom feed
feed = feedparser.parse("https://krebsonsecurity.com/feed/")
print(f"Title: {feed.feed.title}")
print(f"Entries: {len(feed.entries)}")
print(f"Latest: {feed.entries[0].title}")
```

## Domain Filtering

### Blocked Domains (Default)

```bash
REDDIT_BLOCKED_DOMAINS=[
    "youtube.com",
    "youtu.be",
    "twitter.com", 
    "x.com",
    "reddit.com",
    "tiktok.com",
    "instagram.com"
]
```

### Allowed Domains (Optional Whitelist)

```bash
# Only process articles from these domains
REDDIT_ALLOWED_DOMAINS=[
    "github.com",
    "arxiv.org",
    "nvd.nist.gov",
    "cve.mitre.org",
    "krebsonsecurity.com",
    "schneier.com",
    "arstechnica.com"
]
```

## Feed Testing

### Test Configuration

```bash
# Test with minimal feeds first
RSS_FEEDS=["https://krebsonsecurity.com/feed/"]
REDDIT_SUBREDDITS=["netsec"]

# Run ingestion
uv run pydigestor run --step ingest

# Check results
uv run pydigestor status
```

### Expected Results

```
Ingestion Results:
  RSS: 3 articles from 1 feed
  Reddit: 12 articles from 1 subreddit
  Total: 15 articles fetched
  Duplicates: 0 skipped
  Time: 8 seconds
```

## Adding Custom Feeds

### RSS/Atom

```bash
# Add to .env
RSS_FEEDS=[
    # ... existing feeds ...
    "https://your-security-blog.com/feed/"
]
```

### Finding RSS Feeds

Most security blogs provide RSS feeds at:
- `/feed/`
- `/rss/`
- `/atom.xml`
- `/feed.xml`

Or check page source for:
```html
<link rel="alternate" type="application/rss+xml" href="/feed/" />
```

## Feed Maintenance

### Monitor Feed Health

```sql
-- Check feed sources
SELECT 
    metadata->>'feed_source' as source,
    metadata->>'feed_url' as feed,
    COUNT(*) as articles,
    MAX(fetched_at) as last_fetch
FROM articles
GROUP BY source, feed
ORDER BY last_fetch DESC;
```

### Remove Inactive Feeds

If a feed hasn't produced articles in 30 days, consider removing:

```bash
# Check last article from feed
uv run pydigestor feed-stats --feed "https://old-blog.com/feed/"

# Remove from configuration if inactive
```

## Rate Limits

### Reddit
- **Limit:** 30 requests/minute (conservative)
- **Per subreddit:** 1 request every 2 seconds
- **Mitigation:** Built-in rate limiter

### RSS/Atom
- **Limit:** Typically unlimited
- **Best practice:** Check every 1-2 hours (not every minute)
- **Polite:** Include User-Agent header

## Troubleshooting

### Feed Not Updating

```bash
# Check feed manually
curl -v https://feed-url.com/feed/

# Common issues:
# - 404: Feed moved or removed
# - 403: Missing User-Agent header
# - 502/503: Server temporarily down
```

### Reddit 429 Errors

```bash
# Rate limited - reduce frequency
REDDIT_REQUESTS_PER_MINUTE=20  # Lower from 30
```

### Parsing Errors

```python
# Check feed format
import feedparser
feed = feedparser.parse("problematic-feed-url")
print(feed.bozo)  # True if malformed
print(feed.bozo_exception)  # Error details
```

## Summary

**Recommended starting point:**
- 3 RSS feeds (Krebs, Schneier, Ars Technica)
- 2 Reddit sources (r/netsec, r/blueteamsec)
- ~30-40 articles/day
- High signal-to-noise ratio

**Expand as needed based on:**
- Coverage requirements
- Processing capacity
- Storage constraints
- Quality preferences