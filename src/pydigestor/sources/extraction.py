"""Content extraction from URLs using trafilatura and newspaper3k."""

import json
import random
import string
import time
import warnings
from typing import Optional, Tuple
from urllib.parse import urlparse

# Suppress SyntaxWarnings from newspaper3k library (must be before import)
warnings.filterwarnings("ignore", category=SyntaxWarning)

import httpx
import trafilatura
from bs4 import BeautifulSoup
from newspaper import Article as NewspaperArticle
from rich.console import Console

console = Console()

# Known Lemmy instances (link aggregators)
LEMMY_INSTANCES = [
    "infosec.pub",
    "lemmy.world",
    "lemmy.ml",
    "beehaw.org",
    "lemmy.one",
    "programming.dev",
    "sh.itjust.works",
]


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

    def extract(self, url: str) -> tuple[Optional[str], str]:
        """
        Extract content from a URL.

        Args:
            url: URL to extract content from

        Returns:
            Tuple of (extracted text content or None if failed, resolved URL)
        """
        original_url = url
        was_lemmy = False

        # Check if URL previously failed
        if url in self.failed_urls:
            self.metrics["cached_failures"] += 1
            return None, original_url

        # Resolve Lemmy URLs to real destination first
        if self._is_lemmy_url(url):
            was_lemmy = True
            real_url = self._extract_lemmy_destination(url)
            if real_url:
                url = real_url  # Use the real destination URL
            else:
                # Could not resolve Lemmy URL
                self.failed_urls.add(original_url)
                self.metrics["failures"] += 1
                return None, original_url

        self.metrics["total_attempts"] += 1

        # Try trafilatura first
        content = self._extract_with_trafilatura(url)
        if content:
            self.metrics["trafilatura_success"] += 1
            # Return resolved URL only for Lemmy, otherwise return original
            return content, url if was_lemmy else original_url

        # Fallback to newspaper3k
        content = self._extract_with_newspaper(url)
        if content:
            self.metrics["newspaper_success"] += 1
            # Return resolved URL only for Lemmy, otherwise return original
            return content, url if was_lemmy else original_url

        # Both methods failed - cache the URL
        self.failed_urls.add(original_url)
        self.metrics["failures"] += 1
        console.print(f"[yellow]⚠[/yellow] Failed to extract content from {url[:60]}...")
        return None, original_url

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

    def _resolve_medium_canonical(self, url: str, headers: dict) -> Tuple[str, Optional[str]]:
        """
        Resolve Medium URL to canonical form and fetch HTML.

        Args:
            url: Original Medium URL
            headers: HTTP headers to use

        Returns:
            Tuple of (canonical_url, html_content)
        """
        try:
            # Fetch with redirects to resolve /p/ URLs
            response = httpx.get(url, headers=headers, follow_redirects=True, timeout=self.timeout)
            response.raise_for_status()
            html = response.text

            # Parse HTML to extract canonical URL
            soup = BeautifulSoup(html, "html.parser")

            # Try <link rel="canonical">
            canonical_link = soup.find("link", rel="canonical")
            if canonical_link and canonical_link.get("href"):
                canonical_url = canonical_link["href"]
                console.print(f"[dim]→ Resolved canonical: {canonical_url[:60]}...[/dim]")
                return canonical_url, html

            # Fallback to <meta property="og:url">
            og_url = soup.find("meta", property="og:url")
            if og_url and og_url.get("content"):
                canonical_url = og_url["content"]
                console.print(f"[dim]→ Resolved via og:url: {canonical_url[:60]}...[/dim]")
                return canonical_url, html

            # No canonical found, return original
            return url, html

        except Exception as e:
            console.print(f"[dim]→ Canonical resolution failed: {e}[/dim]")
            return url, None

    def _classify_medium_url(self, url: str) -> str:
        """
        Classify Medium URL type.

        Args:
            url: Medium URL to classify

        Returns:
            URL type: "short" (/p/), "subdomain" (user.medium.com), or "standard" (medium.com/@user)
        """
        parsed = urlparse(url)

        # Short URL: /p/{id}
        if parsed.path.startswith("/p/"):
            return "short"

        # Subdomain blog: user.medium.com
        if parsed.netloc.endswith(".medium.com") and parsed.netloc != "medium.com":
            return "subdomain"

        # Standard: medium.com/@user or medium.com/publication
        return "standard"

    def _prepare_medium_url(self, url: str, url_type: str) -> str:
        """
        Prepare Medium URL for fetching based on type.

        Args:
            url: Canonical Medium URL
            url_type: URL type from _classify_medium_url

        Returns:
            Fetch URL (with /m/ for eligible URLs)
        """
        # Only apply /m/ to standard medium.com articles
        if url_type == "standard":
            console.print(f"[dim]→ Using /m/ endpoint for standard URL[/dim]")
            return url.replace("medium.com/", "medium.com/m/", 1)

        # For short and subdomain, use original
        console.print(f"[dim]→ Using original URL ({url_type} type)[/dim]")
        return url

    def _extract_from_json_ld(self, html: str) -> Optional[str]:
        """
        Extract article content from JSON-LD structured data.

        Args:
            html: HTML content

        Returns:
            Article body from JSON-LD or None
        """
        try:
            soup = BeautifulSoup(html, "html.parser")

            # Find script tags with JSON-LD
            for script in soup.find_all("script", type="application/ld+json"):
                if script.string:
                    try:
                        data = json.loads(script.string)

                        # Handle single object or array
                        data_list = data if isinstance(data, list) else [data]

                        for item in data_list:
                            # Look for articleBody in any object
                            if isinstance(item, dict):
                                body = item.get("articleBody")
                                if body and len(body.strip()) > 100:
                                    console.print(f"[dim]→ Extracted from JSON-LD[/dim]")
                                    return body.strip()
                    except json.JSONDecodeError:
                        continue

            return None

        except Exception as e:
            console.print(f"[dim]→ JSON-LD extraction failed: {e}[/dim]")
            return None

    def _is_lemmy_url(self, url: str) -> bool:
        """
        Check if URL is from a Lemmy instance.

        Args:
            url: URL to check

        Returns:
            True if URL is from a known Lemmy instance
        """
        parsed = urlparse(url)
        domain = parsed.netloc.lower()

        # Remove www. prefix if present
        if domain.startswith("www."):
            domain = domain[4:]

        return domain in LEMMY_INSTANCES or "/post/" in parsed.path

    def _extract_lemmy_destination(self, url: str) -> Optional[str]:
        """
        Extract the real destination URL from a Lemmy post page.

        Args:
            url: Lemmy post URL

        Returns:
            Real destination URL or None if not found
        """
        try:
            console.print(f"[dim]→ Resolving Lemmy destination: {url[:60]}...[/dim]")

            parsed = urlparse(url)

            # Extract post ID from URL (e.g., /post/40102015)
            path_parts = parsed.path.split("/")
            post_id = None
            for i, part in enumerate(path_parts):
                if part == "post" and i + 1 < len(path_parts):
                    post_id = path_parts[i + 1]
                    break

            if not post_id:
                console.print("[yellow]⚠[/yellow] Could not extract post ID from Lemmy URL")
                return None

            # Try Lemmy API first (more reliable)
            api_url = f"{parsed.scheme}://{parsed.netloc}/api/v3/post?id={post_id}"

            # Use simple headers for API request (avoid compression issues)
            api_headers = {
                "User-Agent": "pyDigestor/0.1.0",
                "Accept": "application/json",
                "Accept-Encoding": "identity",  # Disable compression to avoid encoding issues
            }

            try:
                response = httpx.get(
                    api_url,
                    timeout=self.timeout,
                    follow_redirects=True,
                    headers=api_headers
                )
                response.raise_for_status()

                # Try to parse JSON
                try:
                    data = response.json()

                    # Extract URL from API response
                    if "post_view" in data and "post" in data["post_view"]:
                        post_url = data["post_view"]["post"].get("url")
                        if post_url and not self._is_lemmy_url(post_url):
                            console.print(f"[dim]→ Found destination (API): {post_url[:60]}...[/dim]")
                            return post_url
                except (ValueError, KeyError) as json_error:
                    console.print(f"[dim]→ API JSON parse failed: {json_error}[/dim]")

            except Exception as api_error:
                console.print(f"[dim]→ Lemmy API failed, falling back to HTML: {api_error}[/dim]")

            # Fallback to HTML scraping
            response = httpx.get(url, timeout=self.timeout, follow_redirects=True, headers=headers)
            response.raise_for_status()

            # Parse HTML
            soup = BeautifulSoup(response.text, "html.parser")

            # Look for external link
            # Lemmy uses <a class="link-external" or "external-link">
            external_link = soup.find("a", class_=["external-link", "link-external"])

            if external_link and external_link.get("href"):
                real_url = external_link["href"]
                console.print(f"[dim]→ Found destination (HTML): {real_url[:60]}...[/dim]")
                return real_url

            # Alternative: look for meta tags
            og_url = soup.find("meta", property="og:url")
            if og_url and og_url.get("content"):
                content_url = og_url["content"]
                # Make sure it's not the Lemmy URL itself
                if not self._is_lemmy_url(content_url):
                    console.print(f"[dim]→ Found og:url: {content_url[:60]}...[/dim]")
                    return content_url

            # Alternative: look in post body for links
            post_body = soup.find("div", class_=["post-body", "md-div"])
            if post_body:
                first_link = post_body.find("a", href=True)
                if first_link:
                    link_url = first_link["href"]
                    if not self._is_lemmy_url(link_url) and link_url.startswith("http"):
                        console.print(f"[dim]→ Found link in post: {link_url[:60]}...[/dim]")
                        return link_url

            console.print("[yellow]⚠[/yellow] Could not extract destination from Lemmy post")
            return None

        except Exception as e:
            console.print(f"[yellow]⚠[/yellow] Error resolving Lemmy URL: {e}")
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
            # Check if this is a Medium URL
            is_medium = "medium.com" in url.lower()

            # Get appropriate headers (with cookies for Medium)
            headers = self._get_mobile_headers(include_cookies=is_medium)

            html_content = None
            fetch_url = url

            # Special handling for Medium URLs
            if is_medium:
                # Step 1: Resolve canonical URL (handles /p/ redirects and extracts HTML)
                canonical_url, initial_html = self._resolve_medium_canonical(url, headers)
                html_content = initial_html

                # Step 2: Classify URL type
                url_type = self._classify_medium_url(canonical_url)

                # Step 3: Prepare fetch URL (apply /m/ only for standard medium.com)
                fetch_url = self._prepare_medium_url(canonical_url, url_type)

                # Step 4: Try JSON-LD extraction first (bypasses paywalls)
                if html_content:
                    json_content = self._extract_from_json_ld(html_content)
                    if json_content:
                        return json_content

                # If canonical differs from fetch_url, need to re-fetch
                if fetch_url != canonical_url and url_type == "standard":
                    response = httpx.get(fetch_url, timeout=self.timeout, follow_redirects=True, headers=headers)
                    response.raise_for_status()
                    html_content = response.text
            else:
                # Non-Medium: standard fetch
                response = httpx.get(fetch_url, timeout=self.timeout, follow_redirects=True, headers=headers)
                response.raise_for_status()
                html_content = response.text

            # If we don't have HTML yet, fetch it
            if not html_content:
                response = httpx.get(fetch_url, timeout=self.timeout, follow_redirects=True, headers=headers)
                response.raise_for_status()
                html_content = response.text

            # Extract with trafilatura
            content = trafilatura.extract(
                html_content.encode() if isinstance(html_content, str) else html_content,
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

            # Get headers
            headers = self._get_mobile_headers(include_cookies=is_medium)

            html_content = None
            fetch_url = url

            # Special handling for Medium URLs (same as trafilatura)
            if is_medium:
                # Resolve canonical URL
                canonical_url, initial_html = self._resolve_medium_canonical(url, headers)

                # Classify URL type
                url_type = self._classify_medium_url(canonical_url)

                # Prepare fetch URL (apply /m/ only for standard medium.com)
                fetch_url = self._prepare_medium_url(canonical_url, url_type)

                # Use initial HTML if available, otherwise fetch
                if initial_html:
                    html_content = initial_html
                elif fetch_url != canonical_url and url_type == "standard":
                    response = httpx.get(fetch_url, timeout=self.timeout, follow_redirects=True, headers=headers)
                    response.raise_for_status()
                    html_content = response.text

            # Create article
            article = NewspaperArticle(fetch_url)
            article.config.browser_user_agent = headers["User-Agent"]
            article.config.request_timeout = self.timeout

            # Use pre-fetched HTML or download
            if html_content:
                article.set_html(html_content)
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
