"""Content extraction from URLs using trafilatura and newspaper3k."""

import random
import string
import time
import warnings
from typing import Optional

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

    def _generate_medium_cookies(self) -> str:
        """
        Generate realistic Medium session cookies with proper entropy.

        Returns:
            Cookie string with realistic session data
        """
        # Generate random hex strings for UIDs and session IDs
        uid_suffix = ''.join(random.choices(string.hexdigits.lower(), k=12))

        # Generate base64-like session ID (mimics real Medium sessions)
        session_chars = string.ascii_letters + string.digits + '+/='
        sid_part = ''.join(random.choices(session_chars, k=64))

        # Generate Cloudflare UVID
        cfuvid = ''.join(random.choices(string.ascii_letters + string.digits, k=43))

        # Generate Google Analytics client ID (10 digit number)
        ga_client_id = ''.join(random.choices(string.digits, k=10))

        # Current timestamp
        timestamp = int(time.time())

        # Generate Cloudflare clearance token
        cf_clearance = ''.join(random.choices(string.ascii_letters + string.digits + '_-', k=43))

        # Build cookie string
        cookies = [
            f"uid=lo_{uid_suffix}",
            f"sid=1:/{sid_part}",
            f"_cfuvid={cfuvid}-{timestamp}-0.0.1.1-604800000",
            f"_ga=GA1.1.{ga_client_id}.{timestamp}",
            f"cf_clearance={cf_clearance}-{timestamp}-1.2.1.1-ufezVnKjunZ26RFSyaVUg",
            f"_ga_7JY7T788PK=GS2.1.s{timestamp}$o1$g1$t{timestamp}$j58$l0$h0",
            f"_dd_s=rum=0&expire={timestamp + 900000}",
        ]

        return "; ".join(cookies)

    def _get_mobile_headers(self, include_cookies: bool = False) -> dict:
        """
        Get mobile browser headers for requests.

        Args:
            include_cookies: Whether to include Medium session cookies

        Returns:
            Dictionary of HTTP headers
        """
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

        if include_cookies:
            headers["Cookie"] = self._generate_medium_cookies()

        return headers

    def _prepare_medium_url(self, url: str) -> str:
        """
        Convert Medium URL to mobile endpoint.

        Args:
            url: Original Medium URL

        Returns:
            Mobile endpoint URL (or original if short URL format)
        """
        # Short URLs (/p/{id}) don't support mobile endpoint - return as-is
        if "/p/" in url:
            console.print(f"[dim]→ Medium short URL (keeping original): {url[:60]}...[/dim]")
            return url

        # Convert full URLs to mobile endpoint: medium.com/... -> medium.com/m/...
        return url.replace("medium.com/", "medium.com/m/", 1)

    def _extract_with_trafilatura(self, url: str) -> Optional[str]:
        """
        Extract content using trafilatura.

        Args:
            url: URL to extract from

        Returns:
            Extracted content or None if failed
        """
        try:
            # Check if this is a Medium URL
            is_medium = "medium.com" in url.lower()

            # Get appropriate headers (with cookies for Medium)
            headers = self._get_mobile_headers(include_cookies=is_medium)

            # Use mobile endpoint for Medium (except short URLs)
            fetch_url = self._prepare_medium_url(url) if is_medium else url

            # Debug logging for Medium URLs
            if is_medium and fetch_url != url:
                console.print(f"[dim]→ Using mobile endpoint: {fetch_url[:60]}...[/dim]")

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
            # Check if this is a Medium URL
            is_medium = "medium.com" in url.lower()

            # Use mobile endpoint for Medium
            fetch_url = self._prepare_medium_url(url) if is_medium else url

            # Get headers (newspaper3k will use these if configured)
            headers = self._get_mobile_headers(include_cookies=is_medium)

            # Create article with mobile URL
            article = NewspaperArticle(fetch_url)

            # Set request headers for newspaper3k
            article.set_html(None)  # Clear any cached HTML
            article.config.browser_user_agent = headers["User-Agent"]
            article.config.request_timeout = self.timeout

            # If Medium, we need to manually fetch with our headers
            if is_medium:
                response = httpx.get(fetch_url, timeout=self.timeout, follow_redirects=True, headers=headers)
                response.raise_for_status()
                article.set_html(response.text)
                article.parse()
            else:
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
