"""Content extraction from URLs using trafilatura and newspaper3k."""

from typing import Optional
import time
import warnings

# Suppress SyntaxWarnings from newspaper3k library (must be before import)
warnings.filterwarnings("ignore", category=SyntaxWarning)

import httpx
import trafilatura
from newspaper import Article as NewspaperArticle
from rich.console import Console

console = Console()


class ContentExtractor:
    """
    Extract article content from URLs.

    Uses trafilatura as the primary method with newspaper3k as fallback.
    Handles timeouts, errors, and caches failures to avoid retrying bad URLs.
    """

    def __init__(self, timeout: int = 10, max_retries: int = 2):
        """
        Initialize content extractor.

        Args:
            timeout: HTTP request timeout in seconds
            max_retries: Maximum number of retry attempts
        """
        self.timeout = timeout
        self.max_retries = max_retries
        self.failed_urls = set()  # Cache of URLs that failed extraction
        self.metrics = {
            "total_attempts": 0,
            "trafilatura_success": 0,
            "newspaper_success": 0,
            "failures": 0,
            "cached_failures": 0,
        }

    def extract(self, url: str) -> Optional[str]:
        """
        Extract content from a URL.

        Args:
            url: URL to extract content from

        Returns:
            Extracted text content or None if extraction failed
        """
        # Check if URL previously failed
        if url in self.failed_urls:
            self.metrics["cached_failures"] += 1
            return None

        self.metrics["total_attempts"] += 1

        # Try trafilatura first
        content = self._extract_with_trafilatura(url)
        if content:
            self.metrics["trafilatura_success"] += 1
            return content

        # Fallback to newspaper3k
        content = self._extract_with_newspaper(url)
        if content:
            self.metrics["newspaper_success"] += 1
            return content

        # Both methods failed - cache the URL
        self.failed_urls.add(url)
        self.metrics["failures"] += 1
        console.print(f"[yellow]⚠[/yellow] Failed to extract content from {url[:60]}...")
        return None

    def _extract_with_trafilatura(self, url: str) -> Optional[str]:
        """
        Extract content using trafilatura.

        Args:
            url: URL to extract from

        Returns:
            Extracted content or None if failed
        """
        try:
            # Mobile browser headers (better for bot detection)
            headers = {
                "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate, br",
                "Referer": "https://www.google.com/",
                "DNT": "1",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "cross-site",
            }

            # For Medium URLs, add session-like cookies and use mobile endpoint
            fetch_url = url
            if "medium.com" in url.lower():
                # Convert to mobile endpoint: medium.com/... -> medium.com/m/...
                fetch_url = url.replace("medium.com/", "medium.com/m/", 1)

                # Add session-like cookies to appear as logged-in user
                headers["Cookie"] = "uid=lo_123456789; sid=1:abc123def456; _ga=GA1.2.123456789.1234567890"

            # Download content with timeout
            response = httpx.get(fetch_url, timeout=self.timeout, follow_redirects=True, headers=headers)
            response.raise_for_status()

            # Extract with trafilatura
            content = trafilatura.extract(
                response.content,
                include_comments=False,
                include_tables=False,
                no_fallback=False,
            )

            # Validate content
            if content and len(content.strip()) > 100:
                return content.strip()

            return None

        except httpx.TimeoutException:
            console.print(f"[yellow]⏱[/yellow] Timeout extracting (trafilatura): {url[:60]}...")
            return None
        except httpx.HTTPError as e:
            console.print(f"[yellow]HTTP error (trafilatura):[/yellow] {url[:60]}... - {e}")
            return None
        except Exception as e:
            console.print(f"[yellow]Error (trafilatura):[/yellow] {url[:60]}... - {e}")
            return None

    def _extract_with_newspaper(self, url: str) -> Optional[str]:
        """
        Extract content using newspaper3k as fallback.

        Args:
            url: URL to extract from

        Returns:
            Extracted content or None if failed
        """
        try:
            article = NewspaperArticle(url)
            article.download()
            article.parse()

            # Validate content
            if article.text and len(article.text.strip()) > 100:
                return article.text.strip()

            return None

        except Exception as e:
            console.print(f"[yellow]Error (newspaper3k):[/yellow] {url[:60]}... - {e}")
            return None

    def get_metrics(self) -> dict:
        """
        Get extraction metrics.

        Returns:
            Dictionary with extraction statistics
        """
        success_rate = 0
        if self.metrics["total_attempts"] > 0:
            total_success = (
                self.metrics["trafilatura_success"] + self.metrics["newspaper_success"]
            )
            success_rate = (total_success / self.metrics["total_attempts"]) * 100

        return {
            **self.metrics,
            "success_rate": round(success_rate, 2),
        }

    def reset_metrics(self):
        """Reset extraction metrics."""
        self.metrics = {
            "total_attempts": 0,
            "trafilatura_success": 0,
            "newspaper_success": 0,
            "failures": 0,
            "cached_failures": 0,
        }
