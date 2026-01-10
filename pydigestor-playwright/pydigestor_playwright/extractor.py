"""Playwright-based content extractor for JavaScript-heavy websites."""

import asyncio
from typing import Optional, Tuple
from urllib.parse import urlparse

from playwright.async_api import async_playwright, Browser, Page, TimeoutError as PlaywrightTimeout
from rich.console import Console

console = Console()


class PlaywrightExtractor:
    """
    Content extractor using Playwright for JavaScript-heavy sites.

    This extractor uses browser automation to handle sites that require:
    - JavaScript rendering
    - Cookie consent interactions
    - Dynamic content loading
    - Anti-bot protection bypass via realistic user agents
    """

    def __init__(self, headless: bool = True, timeout: int = 30000):
        """
        Initialize Playwright extractor.

        Args:
            headless: Run browser in headless mode (default: True)
            timeout: Page load timeout in milliseconds (default: 30000)
        """
        self.headless = headless
        self.timeout = timeout
        self._browser: Optional[Browser] = None

    async def _get_browser(self) -> Browser:
        """
        Get or create browser instance.

        Returns:
            Playwright Browser instance
        """
        if self._browser is None or not self._browser.is_connected():
            playwright = await async_playwright().start()
            self._browser = await playwright.chromium.launch(headless=self.headless)
        return self._browser

    async def _close_browser(self):
        """Close browser instance if open."""
        if self._browser and self._browser.is_connected():
            await self._browser.close()
            self._browser = None

    async def _handle_cookie_consent(self, page: Page) -> bool:
        """
        Attempt to accept cookie consent banners.

        Args:
            page: Playwright Page instance

        Returns:
            True if consent button was clicked, False otherwise
        """
        # Common cookie consent button selectors
        cookie_selectors = [
            'button:has-text("Accept")',
            'button:has-text("Agree")',
            'button:has-text("OK")',
            'button:has-text("Accept all")',
            'button:has-text("Accept cookies")',
            'button:has-text("I agree")',
            '[id*="accept" i]',
            '[class*="accept" i]',
            '[class*="cookie" i] button',
            '.cookie-consent button',
            '#onetrust-accept-btn-handler',  # OneTrust
            '.js-accept-cookies',
        ]

        for selector in cookie_selectors:
            try:
                # Short timeout - we don't want to wait long if button doesn't exist
                await page.click(selector, timeout=2000)
                console.print(f"[dim]→ Clicked cookie consent: {selector}[/dim]")
                # Wait a moment for any animations/transitions
                await page.wait_for_timeout(1000)
                return True
            except PlaywrightTimeout:
                continue
            except Exception:
                continue

        return False

    async def _extract_content(self, page: Page) -> Tuple[Optional[str], Optional[str]]:
        """
        Extract article content and title from page.

        Args:
            page: Playwright Page instance

        Returns:
            Tuple of (content, title)
        """
        # Try multiple content selectors in priority order
        content_selectors = [
            'article',
            'main',
            '[role="main"]',
            '.article-content',
            '.post-content',
            '.entry-content',
            '#content',
            'body',
        ]

        content = None
        for selector in content_selectors:
            try:
                element = await page.query_selector(selector)
                if element:
                    text = await element.inner_text()
                    if text and len(text.strip()) > 100:
                        content = text.strip()
                        console.print(f"[dim]→ Extracted content from: {selector}[/dim]")
                        break
            except Exception:
                continue

        # Extract title
        title = None
        try:
            title = await page.title()
        except Exception:
            pass

        return content, title

    async def _extract_async(self, url: str) -> Tuple[Optional[str], dict]:
        """
        Async extraction with multiple strategies.

        Args:
            url: URL to extract from

        Returns:
            Tuple of (content, metadata)
        """
        metadata = {
            "extraction_method": "playwright",
            "strategy": None,
            "title": None,
            "error": None,
        }

        browser = None
        try:
            console.print(f"[blue]→ Using Playwright for:[/blue] {url[:60]}...")

            # Get or create browser
            browser = await self._get_browser()

            # Create new page with realistic user agent
            page = await browser.new_page(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )

            # Strategy 1: Basic load with networkidle
            try:
                metadata["strategy"] = "networkidle"
                await page.goto(url, wait_until="networkidle", timeout=self.timeout)
            except PlaywrightTimeout:
                # Fallback: just wait for domcontentloaded
                console.print("[dim]→ networkidle timeout, trying domcontentloaded[/dim]")
                metadata["strategy"] = "domcontentloaded"
                await page.goto(url, wait_until="domcontentloaded", timeout=self.timeout)

            # Strategy 2: Handle cookie consent
            await self._handle_cookie_consent(page)

            # Strategy 3: Wait for dynamic content to load
            # Give JavaScript time to render
            await page.wait_for_timeout(2000)

            # Strategy 4: Try to detect and wait for key content
            # Common indicators that content has loaded
            content_indicators = ['article', 'main', '[role="main"]']
            for indicator in content_indicators:
                try:
                    await page.wait_for_selector(indicator, timeout=5000)
                    console.print(f"[dim]→ Content indicator found: {indicator}[/dim]")
                    break
                except PlaywrightTimeout:
                    continue

            # Extract content
            content, title = await self._extract_content(page)

            metadata["title"] = title

            # Close page
            await page.close()

            if content and len(content) > 100:
                console.print(f"[green]✓[/green] Playwright extraction: {len(content)} chars")
                return content, metadata
            else:
                console.print(
                    f"[yellow]⚠[/yellow] Playwright extracted insufficient content ({len(content) if content else 0} chars)"
                )
                metadata["error"] = "Insufficient content extracted"
                return None, metadata

        except Exception as e:
            console.print(f"[yellow]Playwright extraction error:[/yellow] {e}")
            metadata["error"] = str(e)
            return None, metadata

    def extract(self, url: str) -> Tuple[Optional[str], dict]:
        """
        Extract content from URL using Playwright.

        This is the main entry point called by the extraction pattern handler.

        Args:
            url: URL to extract from

        Returns:
            Tuple of (content, metadata)
        """
        # Run async extraction in event loop
        try:
            # Try to get existing event loop
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If loop is already running, create a new one for this operation
                # This can happen in some async contexts
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    return loop.run_until_complete(self._extract_async(url))
                finally:
                    loop.close()
            else:
                return loop.run_until_complete(self._extract_async(url))
        except RuntimeError:
            # No event loop exists, create one
            return asyncio.run(self._extract_async(url))

    def __del__(self):
        """Cleanup browser on deletion."""
        # Best effort cleanup
        try:
            if self._browser:
                asyncio.run(self._close_browser())
        except Exception:
            pass
