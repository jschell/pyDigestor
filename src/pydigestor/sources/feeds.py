"""RSS/Atom feed parsing and fetching."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from urllib.parse import urlparse
import hashlib

import feedparser
import httpx
from rich.console import Console

console = Console()


@dataclass
class FeedEntry:
    """Common format for feed entries from RSS/Atom feeds."""

    source_id: str  # Unique ID for deduplication
    url: str  # Target URL (where the article lives)
    title: str
    content: Optional[str] = None
    summary: Optional[str] = None
    published_at: Optional[datetime] = None
    author: Optional[str] = None
    tags: list[str] = None

    def __post_init__(self):
        """Initialize mutable defaults."""
        if self.tags is None:
            self.tags = []

    @classmethod
    def from_feedparser(cls, entry: dict, feed_url: str) -> Optional["FeedEntry"]:
        """
        Convert a feedparser entry to FeedEntry format.

        Args:
            entry: feedparser entry dict
            feed_url: URL of the feed (for generating source_id)

        Returns:
            FeedEntry instance or None if entry is invalid
        """
        # Extract URL (link is required)
        url = entry.get("link")
        if not url:
            return None

        # Extract title (required)
        title = entry.get("title", "").strip()
        if not title:
            return None

        # Generate unique source_id from feed URL + entry link
        source_id = cls._generate_source_id(feed_url, url)

        # Extract content (prefer content over summary)
        content = None
        if "content" in entry and entry.content:
            content = entry.content[0].get("value", "")
        elif "summary" in entry:
            content = entry.get("summary", "")

        # Extract summary (if different from content)
        summary = entry.get("summary", "")
        if summary == content:
            summary = None

        # Extract published date
        published_at = None
        if "published_parsed" in entry and entry.published_parsed:
            try:
                published_at = datetime(*entry.published_parsed[:6])
            except (TypeError, ValueError):
                pass
        elif "updated_parsed" in entry and entry.updated_parsed:
            try:
                published_at = datetime(*entry.updated_parsed[:6])
            except (TypeError, ValueError):
                pass

        # Extract author
        author = entry.get("author", None)

        # Extract tags
        tags = []
        if "tags" in entry:
            tags = [tag.get("term", "") for tag in entry.tags if tag.get("term")]

        return cls(
            source_id=source_id,
            url=url,
            title=title,
            content=content,
            summary=summary,
            published_at=published_at,
            author=author,
            tags=tags,
        )

    @staticmethod
    def _generate_source_id(feed_url: str, entry_url: str) -> str:
        """
        Generate a unique source_id from feed URL and entry URL.

        Format: rss:{feed_domain}:{url_hash}
        """
        feed_domain = urlparse(feed_url).netloc
        url_hash = hashlib.md5(entry_url.encode()).hexdigest()[:12]
        return f"rss:{feed_domain}:{url_hash}"


class RSSFeedSource:
    """Fetches and parses RSS/Atom feeds."""

    def __init__(self, feed_url: str, timeout: int = 30):
        """
        Initialize RSS feed source.

        Args:
            feed_url: URL of the RSS/Atom feed
            timeout: HTTP request timeout in seconds
        """
        self.feed_url = feed_url
        self.timeout = timeout

    def fetch(self) -> list[FeedEntry]:
        """
        Fetch and parse the RSS/Atom feed.

        Returns:
            List of FeedEntry objects

        Raises:
            Exception: If feed cannot be fetched or parsed
        """
        console.print(f"[blue]Fetching feed:[/blue] {self.feed_url}")

        try:
            # Fetch feed with httpx
            response = httpx.get(self.feed_url, timeout=self.timeout, follow_redirects=True)
            response.raise_for_status()

            # Parse with feedparser
            feed = feedparser.parse(response.content)

            # Check for parse errors
            if feed.bozo:
                console.print(f"[yellow]Feed parse warning:[/yellow] {feed.get('bozo_exception', 'Unknown error')}")

            # Convert entries to FeedEntry format
            entries = []
            for entry in feed.entries:
                feed_entry = FeedEntry.from_feedparser(entry, self.feed_url)
                if feed_entry:
                    entries.append(feed_entry)

            console.print(f"[green]✓[/green] Fetched {len(entries)} entries from {self.feed_url}")
            return entries

        except httpx.HTTPError as e:
            console.print(f"[red]✗[/red] HTTP error fetching {self.feed_url}: {e}")
            raise
        except Exception as e:
            console.print(f"[red]✗[/red] Error parsing {self.feed_url}: {e}")
            raise
