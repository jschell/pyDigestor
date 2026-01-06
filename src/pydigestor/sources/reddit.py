"""Reddit API integration for fetching security-related posts."""

import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import urlparse

import httpx
from rich.console import Console

from pydigestor.sources.feeds import FeedEntry
from pydigestor.utils.rate_limit import RateLimiter

console = Console()


@dataclass
class RedditPost:
    """Represents a Reddit post with security-relevant fields."""

    id: str
    title: str
    url: str  # External URL (if link post)
    permalink: str  # Reddit permalink
    created_utc: float
    score: int
    author: str
    subreddit: str
    is_self: bool  # True for text posts
    selftext: Optional[str] = None  # Body text for self posts
    domain: Optional[str] = None  # Domain of external link


class QualityFilter:
    """Filter Reddit posts by quality criteria."""

    def __init__(
        self,
        max_age_hours: int = 24,
        min_score: int = 0,
        blocked_domains: Optional[list[str]] = None,
    ):
        """
        Initialize quality filter.

        Args:
            max_age_hours: Maximum age of posts in hours
            min_score: Minimum score (upvotes) required
            blocked_domains: List of domains to block (e.g., youtube.com, twitter.com)
        """
        self.max_age_hours = max_age_hours
        self.min_score = min_score
        self.blocked_domains = set(blocked_domains or [])

        # Add common blocked domains
        self.blocked_domains.update([
            "youtube.com",
            "youtu.be",
            "twitter.com",
            "x.com",
            "reddit.com",  # Skip internal reddit links
        ])

    def should_process(self, post: dict) -> bool:
        """
        Determine if a post should be processed.

        Args:
            post: Reddit post dict from API

        Returns:
            True if post passes all filters, False otherwise
        """
        # Check age (recency)
        created_utc = post.get("created_utc", 0)
        age_hours = (time.time() - created_utc) / 3600
        if age_hours > self.max_age_hours:
            return False

        # Check score
        score = post.get("score", 0)
        if score < self.min_score:
            return False

        # Check for blocked domains
        url = post.get("url", "")
        if url:
            domain = urlparse(url).netloc.lower()
            # Remove www. prefix
            domain = domain.replace("www.", "")

            # Check if domain is blocked
            for blocked in self.blocked_domains:
                if blocked in domain:
                    return False

        # Skip self posts with no external content
        is_self = post.get("is_self", False)
        selftext = post.get("selftext", "").strip()
        if is_self and len(selftext) < 50:
            # Self post with very little text - likely low quality
            return False

        return True

    def calculate_priority(self, post: dict) -> float:
        """
        Calculate priority score for a post (higher = more important).

        Based on recency - fresher posts get higher priority.

        Args:
            post: Reddit post dict

        Returns:
            Priority score (0.0 to 1.0)
        """
        created_utc = post.get("created_utc", 0)
        age_hours = (time.time() - created_utc) / 3600

        # Normalize: 0 hours = 1.0 priority, 24 hours = 0.0 priority
        priority = max(0.0, 1.0 - (age_hours / self.max_age_hours))
        return priority


class RedditFetcher:
    """Fetch posts from Reddit's JSON API."""

    def __init__(self, user_agent: str = "pyDigestor/0.1.0", rate_limit: int = 30):
        """
        Initialize Reddit fetcher.

        Args:
            user_agent: User agent string for Reddit API
            rate_limit: Maximum requests per minute
        """
        self.user_agent = user_agent
        self.rate_limiter = RateLimiter(calls_per_minute=rate_limit)
        self.base_url = "https://www.reddit.com"

    def fetch_subreddit(
        self,
        subreddit: str,
        sort: str = "new",
        limit: int = 100,
        quality_filter: Optional[QualityFilter] = None,
    ) -> list[FeedEntry]:
        """
        Fetch posts from a subreddit.

        Args:
            subreddit: Subreddit name (without /r/)
            sort: Sort method (new, hot, top, rising)
            limit: Maximum number of posts to fetch
            quality_filter: Optional filter for post quality

        Returns:
            List of FeedEntry objects for valid posts
        """
        console.print(f"[blue]Fetching Reddit:[/blue] /r/{subreddit} ({sort})")

        # Respect rate limit
        self.rate_limiter.wait_if_needed()

        # Build API URL
        url = f"{self.base_url}/r/{subreddit}/{sort}.json?limit={limit}"

        try:
            # Fetch from Reddit API
            response = httpx.get(
                url,
                headers={"User-Agent": self.user_agent},
                timeout=30,
                follow_redirects=True,
            )
            response.raise_for_status()

            data = response.json()

            # Extract posts from response
            posts = []
            if "data" in data and "children" in data["data"]:
                for child in data["data"]["children"]:
                    if child.get("kind") == "t3":  # t3 = link/post
                        post_data = child.get("data", {})

                        # Apply quality filter if provided
                        if quality_filter and not quality_filter.should_process(post_data):
                            continue

                        # Convert to FeedEntry
                        entry = self._post_to_feed_entry(post_data, subreddit)
                        if entry:
                            posts.append(entry)

            console.print(f"[green]✓[/green] Fetched {len(posts)} posts from /r/{subreddit}")
            return posts

        except httpx.HTTPError as e:
            console.print(f"[red]✗[/red] HTTP error fetching /r/{subreddit}: {e}")
            return []
        except Exception as e:
            console.print(f"[red]✗[/red] Error fetching /r/{subreddit}: {e}")
            return []

    def _post_to_feed_entry(self, post: dict, subreddit: str) -> Optional[FeedEntry]:
        """
        Convert a Reddit post to a FeedEntry.

        Args:
            post: Reddit post data dict
            subreddit: Subreddit name

        Returns:
            FeedEntry or None if conversion fails
        """
        # Extract fields
        post_id = post.get("id")
        title = post.get("title", "").strip()
        is_self = post.get("is_self", False)
        url = post.get("url", "")
        permalink = post.get("permalink", "")
        created_utc = post.get("created_utc", 0)
        author = post.get("author", "[deleted]")

        if not post_id or not title:
            return None

        # Generate source_id
        source_id = f"reddit:{subreddit}:{post_id}"

        # Determine target URL
        if is_self:
            # Self post - use Reddit permalink
            target_url = f"https://www.reddit.com{permalink}"
            content = post.get("selftext", "")
        else:
            # Link post - use external URL
            target_url = url
            content = ""

        # Convert timestamp
        published_at = None
        if created_utc:
            try:
                published_at = datetime.fromtimestamp(created_utc, tz=timezone.utc)
            except (ValueError, OSError):
                pass

        return FeedEntry(
            source_id=source_id,
            url=target_url,
            title=title,
            content=content,
            published_at=published_at,
            author=f"u/{author}",
            tags=[f"r/{subreddit}"],
        )
