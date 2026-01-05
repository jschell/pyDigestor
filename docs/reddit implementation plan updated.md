# Reddit Source - Implementation Plan (Updated for Recency Focus)

## Key Changes from Original Plan

**Original Focus:** High-score posts (viral content)  
**Updated Focus:** Fresh posts (breaking news, recent developments)

**Why This Matters:**
- Security news is time-sensitive (CVEs, breaches, vulnerabilities)
- Fresh content has less competition from other aggregators
- Lower initial engagement doesn't mean lower quality
- Recency is a better quality signal for technical content

---

## Target Subreddits for Testing

### Security-Focused (Primary)
1. **r/netsec** - Network security, offensive security, exploits
   - URL: `https://www.reddit.com/r/netsec/new/`
   - Focus: Breaking security research, CVEs, tools
   - Volume: ~20-30 posts/day
   - Quality: High (moderated)

2. **r/blueteamsec** - Defensive security, incident response
   - URL: `https://www.reddit.com/r/blueteamsec/new/`
   - Focus: Defensive tactics, detection, SOC operations
   - Volume: ~10-15 posts/day
   - Quality: Very high (highly moderated)

### Why These Subreddits?
- **Moderated communities** = higher baseline quality
- **Technical focus** = less noise than general tech subs
- **Fresh vulnerabilities** = immediate value to readers
- **Professional audience** = good engagement signals
- **External links** = original research, blog posts, advisories

---

## Updated Configuration Strategy

### Recency-First Filtering

```bash
# .env - Updated for /new sorting

# Reddit Configuration
REDDIT_ENABLED=true

# Security-focused subreddits with /new sorting
REDDIT_SUBREDDITS=["netsec", "blueteamsec"]
REDDIT_SORT=new  # Changed from 'hot' to 'new'
REDDIT_LIMIT=100  # Increased to catch more fresh posts

# Recency-based filtering (instead of score)
REDDIT_MIN_SCORE=0  # Accept posts with any score if fresh
REDDIT_MAX_AGE_HOURS=24  # Only posts from last 24 hours
REDDIT_MIN_COMMENTS=0  # Don't filter by engagement initially

# Fresh post priority
REDDIT_PRIORITY_HOURS=6  # Posts < 6 hours get priority

# Domain filtering (security-specific)
REDDIT_ALLOWED_DOMAINS=[
  "github.com",
  "nvd.nist.gov",
  "cve.mitre.org",
  "securityaffairs.com",
  "bleepingcomputer.com",
  "krebsonsecurity.com",
  "schneier.com"
]
```

---

## Phase 1: Core Fetcher (Week 1)

### Day 1-2: Basic API Integration with /new Support

**Create:** `src/pipeline/sources/reddit.py`

```python
import httpx
from datetime import datetime, timedelta
from typing import Optional
import time

class RateLimiter:
    """Simple rate limiter."""
    def __init__(self, calls_per_minute: int = 30):
        self.min_interval = 60.0 / calls_per_minute
        self.last_call = 0.0
    
    def wait_if_needed(self):
        elapsed = time.time() - self.last_call
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)
        self.last_call = time.time()

class RedditFetcher:
    """Fetch posts from Reddit JSON API with focus on /new."""
    
    def __init__(self):
        self.rate_limiter = RateLimiter(calls_per_minute=30)
        self.headers = {
            "User-Agent": "Mozilla/5.0 (compatible; ContentPipeline/1.0)"
        }
    
    def fetch_subreddit(
        self, 
        subreddit: str, 
        sort: str = "new",  # Changed default to 'new'
        limit: int = 100,   # Increased default
        max_age_hours: int = 24
    ) -> list[dict]:
        """Fetch fresh posts from subreddit.
        
        Args:
            subreddit: Subreddit name (without r/)
            sort: 'new', 'hot', 'top', or 'rising'
            limit: Maximum posts to fetch
            max_age_hours: Only return posts newer than this
        """
        
        self.rate_limiter.wait_if_needed()
        
        url = f"https://www.reddit.com/r/{subreddit}/{sort}.json"
        params = {"limit": limit}
        
        try:
            response = httpx.get(
                url,
                params=params,
                headers=self.headers,
                timeout=10,
                follow_redirects=True
            )
            response.raise_for_status()
            
            data = response.json()
            posts = [child["data"] for child in data["data"]["children"]]
            
            # Filter by age
            cutoff = datetime.utcnow() - timedelta(hours=max_age_hours)
            fresh_posts = [
                p for p in posts 
                if datetime.fromtimestamp(p["created_utc"]) > cutoff
            ]
            
            return fresh_posts
        
        except Exception as e:
            print(f"Error fetching r/{subreddit}: {e}")
            return []
```

**Test:**
```bash
python -c "
from pipeline.sources.reddit import RedditFetcher
from datetime import datetime, timedelta

fetcher = RedditFetcher()

# Fetch fresh posts from security subreddits
for subreddit in ['netsec', 'blueteamsec']:
    posts = fetcher.fetch_subreddit(subreddit, sort='new', max_age_hours=24)
    print(f'\nr/{subreddit}: {len(posts)} fresh posts')
    
    for p in posts[:3]:
        age = datetime.utcnow() - datetime.fromtimestamp(p['created_utc'])
        print(f'  [{age.seconds//3600}h ago] {p[\"title\"][:60]}... ({p[\"score\"]} pts)')
"
```

**Expected Output:**
```
r/netsec: 18 fresh posts
  [2h ago] New CVE-2025-1234: RCE in popular framework... (12 pts)
  [4h ago] Analysis of recent ransomware campaign... (8 pts)
  [6h ago] Open source SIEM alternative released... (15 pts)

r/blueteamsec: 7 fresh posts
  [1h ago] Detecting lateral movement with Sysmon... (5 pts)
  [3h ago] Building a home SOC lab... (9 pts)
  [5h ago] Threat hunting query collection... (11 pts)
```

**Deliverable:** Can fetch fresh posts with recency filtering  
**Time:** 2 days

---

### Day 3-4: Recency-Based Quality Filtering

**Add to:** `src/pipeline/sources/reddit.py`

```python
from urllib.parse import urlparse
from datetime import datetime, timedelta

class QualityFilter:
    """Filter Reddit posts by recency and quality signals.
    
    For /new sorting, recency is the primary quality signal.
    Score is less important for fresh content.
    """
    
    def __init__(
        self, 
        min_score: int = 0,  # Accept any score for fresh posts
        max_age_hours: int = 24,
        min_comments: int = 0,
        priority_hours: int = 6,  # Very fresh posts get priority
        allowed_domains: list[str] = None,
        blocked_domains: list[str] = None,
    ):
        self.min_score = min_score
        self.max_age_hours = max_age_hours
        self.min_comments = min_comments
        self.priority_hours = priority_hours
        
        # Security-specific allowed domains
        self.allowed_domains = set(allowed_domains or [
            "github.com",
            "nvd.nist.gov",
            "cve.mitre.org",
            "cert.org",
            "us-cert.gov",
            "cisa.gov",
        ])
        
        # Always block these
        self.blocked_domains = set(blocked_domains or [
            "youtube.com", "youtu.be",
            "twitter.com", "x.com",
            "reddit.com",
            "tiktok.com",
            "instagram.com",
        ])
    
    def should_process(self, post: dict) -> bool:
        """Determine if post is worth processing."""
        
        # Recency check (primary filter)
        post_age = datetime.utcnow() - datetime.fromtimestamp(post["created_utc"])
        if post_age > timedelta(hours=self.max_age_hours):
            return False
        
        # For very fresh posts, be more lenient
        if post_age < timedelta(hours=self.priority_hours):
            # Fresh posts can have low score
            pass
        else:
            # Older posts need minimum engagement
            if post["score"] < self.min_score:
                return False
        
        # Self-post with no text
        if post["is_self"] and len(post.get("selftext", "")) < 100:
            return False
        
        # Domain filtering for link posts
        if not post["is_self"]:
            domain = self._extract_domain(post["url"])
            
            # Blocked domains
            if domain in self.blocked_domains:
                return False
            
            # If whitelist is configured, enforce it
            if self.allowed_domains and domain not in self.allowed_domains:
                # Allow some flexibility for security blogs
                if not self._is_security_related(domain):
                    return False
        
        return True
    
    def get_priority(self, post: dict) -> int:
        """Calculate priority score (higher = process first).
        
        For /new sorting, fresher posts get higher priority.
        """
        post_age = datetime.utcnow() - datetime.fromtimestamp(post["created_utc"])
        hours_old = post_age.total_seconds() / 3600
        
        # Base priority: inverse of age (fresher = higher)
        priority = 100 - int(hours_old)
        
        # Bonus for engagement
        priority += min(post["score"] // 5, 20)  # Max +20 for score
        priority += min(post["num_comments"] // 2, 10)  # Max +10 for comments
        
        return max(0, priority)
    
    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL."""
        domain = urlparse(url).netloc.lower()
        return domain.replace("www.", "")
    
    def _is_security_related(self, domain: str) -> bool:
        """Check if domain is likely security-related."""
        security_keywords = [
            "security", "sec", "cyber", "cve", "vuln",
            "exploit", "malware", "threat", "infosec"
        ]
        return any(kw in domain for kw in security_keywords)
```

**Test:**
```python
from pipeline.sources.reddit import QualityFilter
from datetime import datetime, timedelta

filter = QualityFilter(
    min_score=0,
    max_age_hours=24,
    priority_hours=6,
    allowed_domains=["github.com", "nvd.nist.gov"]
)

# Very fresh post (2 hours old, low score) - SHOULD PROCESS
fresh_post = {
    "score": 3,
    "created_utc": (datetime.utcnow() - timedelta(hours=2)).timestamp(),
    "is_self": False,
    "num_comments": 1,
    "url": "https://github.com/user/security-tool"
}
assert filter.should_process(fresh_post) == True
assert filter.get_priority(fresh_post) > 90  # High priority

# Older post (20 hours old, low score) - SHOULD SKIP
old_post = {
    "score": 3,
    "created_utc": (datetime.utcnow() - timedelta(hours=20)).timestamp(),
    "is_self": False,
    "num_comments": 1,
    "url": "https://github.com/user/security-tool"
}
assert filter.should_process(old_post) == False

# Fresh post, blocked domain - SHOULD SKIP
blocked_post = {
    "score": 10,
    "created_utc": (datetime.utcnow() - timedelta(hours=1)).timestamp(),
    "is_self": False,
    "num_comments": 5,
    "url": "https://youtube.com/watch"
}
assert filter.should_process(blocked_post) == False

# Fresh CVE announcement - HIGH PRIORITY
cve_post = {
    "score": 5,
    "created_utc": (datetime.utcnow() - timedelta(hours=3)).timestamp(),
    "is_self": False,
    "num_comments": 2,
    "url": "https://nvd.nist.gov/vuln/detail/CVE-2025-1234"
}
assert filter.should_process(cve_post) == True
assert filter.get_priority(cve_post) > 95
```

**Deliverable:** Recency-based filtering with priority scoring  
**Time:** 2 days

---

### Day 5: Updated Configuration

**Update:** `src/pipeline/config.py`

```python
class Settings(BaseSettings):
    # ... existing settings ...
    
    # Reddit Configuration - Recency Focus
    reddit_enabled: bool = True
    reddit_subreddits: list[str] = Field(
        default_factory=lambda: ["netsec", "blueteamsec"]
    )
    reddit_sort: str = "new"  # Changed from 'hot'
    reddit_limit: int = 100  # Increased from 50
    
    # Recency-based filtering
    reddit_min_score: int = 0  # Changed from 10
    reddit_max_age_hours: int = 24
    reddit_priority_hours: int = 6
    reddit_min_comments: int = 0
    
    # Domain filtering (security-focused)
    reddit_allowed_domains: list[str] = Field(
        default_factory=lambda: [
            "github.com",
            "nvd.nist.gov",
            "cve.mitre.org",
            "cert.org",
            "us-cert.gov",
            "cisa.gov",
            "securityaffairs.com",
            "bleepingcomputer.com",
            "krebsonsecurity.com",
            "schneier.com",
        ]
    )
    reddit_blocked_domains: list[str] = Field(
        default_factory=lambda: [
            "youtube.com", "youtu.be",
            "twitter.com", "x.com",
            "reddit.com",
            "tiktok.com",
            "instagram.com",
        ]
    )
```

**Update:** `.env.example`

```bash
# Reddit Configuration - Security Subreddits with /new Focus

REDDIT_ENABLED=true

# Security-focused subreddits
REDDIT_SUBREDDITS=["netsec", "blueteamsec"]

# Sorting: 'new' for breaking news, 'hot' for trending
REDDIT_SORT=new

# Fetch more posts from /new to catch everything fresh
REDDIT_LIMIT=100

# Recency-based filtering (instead of score-based)
REDDIT_MIN_SCORE=0  # Accept any score for fresh posts
REDDIT_MAX_AGE_HOURS=24  # Only posts from last 24 hours
REDDIT_PRIORITY_HOURS=6  # Posts < 6 hours get priority processing
REDDIT_MIN_COMMENTS=0  # Don't require engagement for fresh posts

# Domain filtering for security content
REDDIT_ALLOWED_DOMAINS=[
  "github.com",
  "nvd.nist.gov", 
  "cve.mitre.org",
  "cert.org",
  "us-cert.gov",
  "cisa.gov"
]

REDDIT_BLOCKED_DOMAINS=["youtube.com", "twitter.com", "reddit.com"]
```

**Deliverable:** Configuration optimized for fresh security content  
**Time:** 1 day

---

## Phase 2: Content Extraction (Week 2)

### Day 6-8: Security-Focused Article Extractor

**Add to:** `src/pipeline/sources/reddit.py`

**Install dependencies:**
```bash
uv add trafilatura newspaper3k beautifulsoup4 pdfplumber
```

**Implement with security-specific handling:**

```python
from trafilatura import fetch_url, extract
from newspaper import Article as NewspaperArticle
import pdfplumber
from io import BytesIO
import httpx
import re

class ContentExtractor:
    """Extract article content with security-specific and PDF handling."""
    
    def __init__(self, timeout: int = 10):
        self.timeout = timeout
        self.failed_cache = set()
    
    def is_pdf(self, url: str) -> bool:
        """Check if URL points to PDF via HEAD request."""
        try:
            response = httpx.head(url, follow_redirects=True, timeout=5)
            content_type = response.headers.get('content-type', '').lower()
            return 'application/pdf' in content_type
        except:
            # Fallback to URL pattern
            return url.lower().endswith('.pdf')
    
    def extract(self, url: str, post_title: str = "") -> Optional[str]:
        """Extract article content.
        
        For security content, handles:
        - PDF documents (whitepapers, reports)
        - GitHub READMEs
        - CVE databases
        - Security blogs
        - Technical writeups
        """
        
        # Skip cached failures
        if url in self.failed_cache:
            return None
        
        # Check for PDF first
        if self.is_pdf(url):
            content = self._extract_pdf(url)
            if content:
                return content
        
        # Special handling for known sources
        if "github.com" in url:
            content = self._extract_github(url)
        elif "nvd.nist.gov" in url or "cve.mitre.org" in url:
            content = self._extract_cve(url, post_title)
        else:
            content = self._extract_generic(url)
        
        if not content:
            self.failed_cache.add(url)
        
        return content
    
    def _extract_pdf(self, url: str) -> Optional[str]:
        """Extract text from PDF document."""
        try:
            # Download PDF
            response = httpx.get(url, timeout=self.timeout, follow_redirects=True)
            
            # Verify it's actually a PDF
            if not response.content.startswith(b'%PDF'):
                return None
            
            # Extract text locally
            with pdfplumber.open(BytesIO(response.content)) as pdf:
                text = "\n\n".join(
                    page.extract_text() or "" 
                    for page in pdf.pages
                )
                
                # Filter out empty/too short extractions
                if len(text.strip()) > 200:
                    return text
            
        except Exception as e:
            print(f"PDF extraction failed for {url}: {e}")
        
        return None
    
    def _extract_github(self, url: str) -> Optional[str]:
        """Extract GitHub README or description."""
        try:
            # Trafilatura works well for GitHub
            downloaded = fetch_url(url)
            if downloaded:
                content = extract(downloaded)
                if content and len(content) > 200:
                    return content
        except:
            pass
        return None
    
    def _extract_cve(self, url: str, title: str) -> Optional[str]:
        """Extract CVE information.
        
        For CVE databases, combine title with extracted description.
        """
        try:
            downloaded = fetch_url(url)
            if downloaded:
                content = extract(downloaded)
                if content:
                    # Prepend title for context
                    return f"{title}\n\n{content}"
        except:
            pass
        
        # Fallback: use title as content
        if title and "CVE-" in title:
            return title
        
        return None
    
    def _extract_generic(self, url: str) -> Optional[str]:
        """Standard extraction for blogs and articles."""
        
        # Try trafilatura first (best for articles)
        content = self._try_trafilatura(url)
        if content:
            return content
        
        # Fallback to newspaper3k
        content = self._try_newspaper(url)
        if content:
            return content
        
        return None
    
    def _try_trafilatura(self, url: str) -> Optional[str]:
        """Try trafilatura extraction."""
        try:
            downloaded = fetch_url(url)
            if downloaded:
                content = extract(downloaded)
                if content and len(content) > 300:
                    return content
        except:
            pass
        return None
    
    def _try_newspaper(self, url: str) -> Optional[str]:
        """Try newspaper3k extraction."""
        try:
            article = NewspaperArticle(url)
            article.download()
            article.parse()
            
            if len(article.text) > 300:
                return article.text
        except:
            pass
        return None
```

**Test with security URLs:**
```python
from pipeline.sources.reddit import ContentExtractor

extractor = ContentExtractor()

# Test PDF extraction
pdf_url = "https://example.com/security-whitepaper.pdf"
content = extractor.extract(pdf_url, "Security Whitepaper")
if content:
    print(f"PDF: {len(content)} chars extracted")

# Test GitHub extraction
github_url = "https://github.com/projectdiscovery/nuclei"
content = extractor.extract(github_url, "Nuclei - Fast scanner")
assert content is not None
print(f"GitHub: {len(content)} chars")

# Test CVE extraction
cve_url = "https://nvd.nist.gov/vuln/detail/CVE-2024-1234"
content = extractor.extract(cve_url, "CVE-2024-1234: Critical RCE")
assert content is not None
print(f"CVE: {len(content)} chars")

# Test security blog
blog_url = "https://krebsonsecurity.com/2025/01/article/"
content = extractor.extract(blog_url)
# May or may not succeed depending on site structure
print(f"Blog: {len(content) if content else 0} chars")
```

**Deliverable:** Security-aware content extraction  
**Time:** 3 days

---

## Phase 3: Integration with Priority Processing (Week 3)

### Day 11-12: Priority-Based RedditSource

**Complete:** `src/pipeline/sources/reddit.py`

```python
class RedditSource:
    """Reddit source with priority processing for fresh content."""
    
    def __init__(self, config):
        self.config = config
        self.fetcher = RedditFetcher()
        self.filter = QualityFilter(
            min_score=config.reddit_min_score,
            max_age_hours=config.reddit_max_age_hours,
            priority_hours=config.reddit_priority_hours,
            allowed_domains=config.reddit_allowed_domains,
            blocked_domains=config.reddit_blocked_domains,
        )
        self.extractor = ContentExtractor()
        self.processor = PostProcessor()
    
    def fetch(self) -> list[dict]:
        """Fetch and process Reddit posts, prioritizing fresh content."""
        
        if not self.config.reddit_enabled:
            return []
        
        all_posts = []
        
        # Fetch from all subreddits
        for subreddit in self.config.reddit_subreddits:
            print(f"Fetching r/{subreddit}/new...")
            
            posts = self.fetcher.fetch_subreddit(
                subreddit,
                sort=self.config.reddit_sort,
                limit=self.config.reddit_limit,
                max_age_hours=self.config.reddit_max_age_hours
            )
            
            # Add priority scores
            for post in posts:
                post["_priority"] = self.filter.get_priority(post)
            
            all_posts.extend(posts)
            print(f"  → {len(posts)} fresh posts")
        
        # Sort by priority (process freshest first)
        all_posts.sort(key=lambda p: p["_priority"], reverse=True)
        
        # Process in priority order
        articles = []
        for post in all_posts:
            # Filter
            if not self.filter.should_process(post):
                continue
            
            # Self-post
            if post["is_self"]:
                article = self.processor.process_self_post(post)
                articles.append(article)
            
            # Link post
            else:
                content = self.extractor.extract(post["url"], post["title"])
                if content:
                    article = self.processor.process_link_post(post, content)
                    articles.append(article)
        
        print(f"  → Processed {len(articles)} articles total")
        return articles
```

**Deliverable:** Priority-aware Reddit source  
**Time:** 2 days

---

## Testing Strategy for Security Subreddits

### Initial Test Run

```bash
# Configure for security subreddits
cat > .env << EOF
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/test_db

REDDIT_ENABLED=true
REDDIT_SUBREDDITS=["netsec", "blueteamsec"]
REDDIT_SORT=new
REDDIT_LIMIT=50
REDDIT_MAX_AGE_HOURS=24
REDDIT_MIN_SCORE=0
EOF

# Run ingestion
uv run pipeline run --step ingest
```

### Expected Results

**r/netsec typical yield:**
- Fetched: ~20-30 posts
- After filtering: ~10-15 articles
- Content types:
  - GitHub tools/exploits: 30%
  - Blog posts/writeups: 25%
  - PDF whitepapers/reports: 20%
  - CVE announcements: 15%
  - News articles: 10%

**r/blueteamsec typical yield:**
- Fetched: ~10-15 posts
- After filtering: ~5-8 articles
- Content types:
  - Detection rules/queries: 30%
  - Blog posts: 25%
  - GitHub tools: 20%
  - PDF threat reports: 15%
  - News/advisories: 10%

### Quality Verification

```sql
-- Check fetched articles
SELECT 
    metadata->>'subreddit' as subreddit,
    metadata->>'reddit_score' as score,
    EXTRACT(EPOCH FROM (NOW() - published_at))/3600 as hours_old,
    title
FROM articles
WHERE metadata->>'source_type' LIKE 'reddit%'
    AND published_at > NOW() - INTERVAL '24 hours'
ORDER BY published_at DESC
LIMIT 20;
```

**Look for:**
- ✅ Most posts < 12 hours old
- ✅ Mix of high and low scores (recency matters more)
- ✅ Variety of sources (GitHub, blogs, PDFs, CVEs)
- ✅ No YouTube/Twitter links
- ✅ PDF extraction working for whitepapers/reports

---

## Scheduling Strategy for /new

### Frequent Polling (Recommended)

```bash
# Check every 2 hours for new security posts
0 */2 * * * cd /path/to/pipeline && uv run pipeline run --step ingest

# Or every hour during business hours
0 9-17 * * 1-5 cd /path/to/pipeline && uv run pipeline run --step ingest
```

**Why frequent polling?**
- Fresh security news breaks throughout the day
- Low volume subreddits (10-30 posts/day)
- Avoid missing breaking CVEs or exploits
- Stay ahead of other aggregators

### Alternative: Continuous Monitoring

```python
# Advanced: Long-running process
while True:
    reddit = RedditSource(settings)
    new_articles = reddit.fetch()
    
    if new_articles:
        store_articles(new_articles)
        trigger_pipeline()  # Run triage, extract, etc.
    
    time.sleep(3600)  # Check hourly
```

---

## Performance Expectations

### r/netsec + r/blueteamsec (24 hours)

| Metric | Expected |
|--------|----------|
| Posts fetched | 30-40 |
| After filtering | 15-20 |
| Extraction success | 70-80% |
| Final articles | 12-16 |
| API calls | 2 (one per subreddit) |
| Processing time | 2-3 minutes |

### Cost (LiteLLM + Claude)

Assuming 15 articles/day through pipeline:
- Triage: 15 articles × $0.0001 = $0.0015
- Extract: 12 articles × $0.001 = $0.012
- **Daily:** ~$0.02
- **Monthly:** ~$0.60

Extremely cheap for security content!

---

## Summary of Changes

### Original Plan → Updated Plan

| Aspect | Original | Updated |
|--------|----------|---------|
| **Subreddits** | technology, programming | netsec, blueteamsec |
| **Sort** | hot (viral) | new (fresh) |
| **Score filter** | Min 10-50 | Min 0 (any) |
| **Age filter** | None | 24 hours max |
| **Priority** | Score-based | Recency-based |
| **Domains** | General tech | Security-focused |
| **Polling** | Daily | Every 2 hours |
| **Focus** | Popular content | Breaking news |

### Why This Works Better

1. **Lower competition** - Fresh posts haven't been aggregated elsewhere
2. **Time-sensitive** - Security news has immediate value
3. **Higher quality** - Moderated security communities
4. **Professional audience** - Better engagement signals
5. **Original sources** - GitHub, CVE databases, security blogs

---

## Next Steps

Ready to implement with this recency-focused approach:

1. ✅ Architecture designed for /new sorting
2. ✅ Security subreddits identified
3. ✅ Recency-based filtering defined
4. ✅ Priority processing planned
5. 🔄 Begin Phase 1 implementation

**Start coding?**