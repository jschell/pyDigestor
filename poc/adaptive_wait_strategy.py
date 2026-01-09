"""
Adaptive Wait Strategy for Playwright Web Scraping

Progressive backoff approach that automatically adjusts wait times
based on content retrieval success, eliminating need for per-site configuration.
"""

import asyncio
from typing import Optional, Tuple
from dataclasses import dataclass

from playwright.async_api import Page


@dataclass
class WaitStrategy:
    """Configuration for adaptive wait strategy"""
    min_content_threshold: int = 100  # Minimum chars to consider success
    initial_wait_ms: int = 0          # Start with no extra wait
    max_attempts: int = 4             # Number of retry attempts
    wait_increment_ms: int = 2000     # Increase wait by 2s each retry
    max_total_wait_ms: int = 15000    # Never wait more than 15s total
    enable_scroll: bool = True        # Try scrolling on retries
    enable_cookie_click: bool = True  # Try clicking cookie consent


class AdaptiveContentScraper:
    """
    Adaptive scraper that progressively increases wait times until content is found.

    Strategy progression:
    1. Attempt 1: Basic (0s extra wait)
    2. Attempt 2: +2s wait + cookie consent
    3. Attempt 3: +4s wait + scroll trigger
    4. Attempt 4: +6s wait + multiple scroll + network idle
    """

    def __init__(self, strategy: Optional[WaitStrategy] = None):
        self.strategy = strategy or WaitStrategy()

    async def scrape_with_adaptive_wait(
        self,
        page: Page,
        content_selectors: list[str]
    ) -> Tuple[str, int, dict]:
        """
        Scrape page with adaptive wait strategy.

        Returns:
            Tuple of (content, attempt_number, metadata)
        """
        for attempt in range(1, self.strategy.max_attempts + 1):
            # Calculate wait time for this attempt (progressive backoff)
            extra_wait_ms = min(
                (attempt - 1) * self.strategy.wait_increment_ms,
                self.strategy.max_total_wait_ms
            )

            print(f"  Attempt {attempt}/{self.strategy.max_attempts} "
                  f"(+{extra_wait_ms/1000:.1f}s extra wait)")

            # Try to get content with current strategy
            content = await self._try_extract_content(
                page,
                content_selectors,
                extra_wait_ms,
                attempt
            )

            # Check if we got sufficient content
            if len(content.strip()) >= self.strategy.min_content_threshold:
                metadata = {
                    'success': True,
                    'attempt': attempt,
                    'total_extra_wait_ms': extra_wait_ms,
                    'strategy_level': self._get_strategy_name(attempt)
                }
                print(f"  ✓ Content found on attempt {attempt} "
                      f"({len(content)} chars, +{extra_wait_ms/1000:.1f}s)")
                return content, attempt, metadata

            print(f"  ✗ Insufficient content ({len(content)} chars), retrying...")

        # All attempts failed
        metadata = {
            'success': False,
            'attempt': self.strategy.max_attempts,
            'total_extra_wait_ms': extra_wait_ms,
            'strategy_level': 'all_failed'
        }
        return content, self.strategy.max_attempts, metadata

    async def _try_extract_content(
        self,
        page: Page,
        content_selectors: list[str],
        extra_wait_ms: int,
        attempt: int
    ) -> str:
        """Try to extract content with given wait time and strategy level"""

        # Attempt 1: Basic - just extra wait
        if attempt == 1:
            if extra_wait_ms > 0:
                await page.wait_for_timeout(extra_wait_ms)

        # Attempt 2: Add cookie consent handling
        elif attempt == 2:
            if self.strategy.enable_cookie_click:
                await self._try_click_cookie_consent(page)

            if extra_wait_ms > 0:
                await page.wait_for_timeout(extra_wait_ms)

        # Attempt 3: Add scroll triggering
        elif attempt == 3:
            if self.strategy.enable_cookie_click:
                await self._try_click_cookie_consent(page)

            if extra_wait_ms > 0:
                await page.wait_for_timeout(extra_wait_ms)

            if self.strategy.enable_scroll:
                await self._scroll_to_trigger_loading(page)

        # Attempt 4+: Full strategy with multiple interactions
        else:
            if self.strategy.enable_cookie_click:
                await self._try_click_cookie_consent(page)

            if extra_wait_ms > 0:
                await page.wait_for_timeout(extra_wait_ms)

            if self.strategy.enable_scroll:
                # Multiple scroll attempts
                await self._scroll_to_trigger_loading(page, multi_scroll=True)

            # Final network idle wait
            try:
                await page.wait_for_load_state("networkidle", timeout=5000)
            except Exception:
                pass

        # Extract content
        return await self._extract_content(page, content_selectors)

    async def _try_click_cookie_consent(self, page: Page):
        """Try to click cookie consent button"""
        cookie_selectors = [
            'button:has-text("Accept")',
            'button:has-text("OK")',
            'button:has-text("Agree")',
            'button:has-text("Accept all")',
            '[class*="cookie"] button',
            '[id*="accept"]',
        ]

        for selector in cookie_selectors:
            try:
                await page.click(selector, timeout=1000)
                print(f"    ✓ Clicked cookie consent")
                await page.wait_for_timeout(500)
                return
            except Exception:
                continue

    async def _scroll_to_trigger_loading(self, page: Page, multi_scroll: bool = False):
        """Scroll page to trigger lazy loading"""
        if multi_scroll:
            # Scroll to multiple positions
            positions = [0.25, 0.5, 0.75, 1.0, 0]  # 25%, 50%, 75%, bottom, top
            for pos in positions:
                await page.evaluate(f'window.scrollTo(0, document.body.scrollHeight * {pos})')
                await page.wait_for_timeout(500)
        else:
            # Simple scroll down and back up
            await page.evaluate('window.scrollTo(0, document.body.scrollHeight / 2)')
            await page.wait_for_timeout(1000)
            await page.evaluate('window.scrollTo(0, 0)')
            await page.wait_for_timeout(500)

    async def _extract_content(self, page: Page, content_selectors: list[str]) -> str:
        """Extract content using provided selectors"""
        for selector in content_selectors:
            try:
                element = await page.query_selector(selector)
                if element:
                    content = await element.inner_text()
                    if len(content.strip()) > 50:  # Has some content
                        return content
            except Exception:
                continue
        return ""

    def _get_strategy_name(self, attempt: int) -> str:
        """Get human-readable strategy name for attempt"""
        strategies = {
            1: "basic",
            2: "basic+cookie",
            3: "basic+cookie+scroll",
            4: "full_enhanced"
        }
        return strategies.get(attempt, f"level_{attempt}")


# Example usage in the POC
async def scrape_page_with_adaptive_wait(page: Page, url: str) -> dict:
    """
    Example of using adaptive wait strategy in scraping.

    This replaces the hardcoded per-site logic with automatic adaptation.
    """
    # Navigate to page
    await page.goto(url, wait_until="domcontentloaded", timeout=30000)

    # Wait for initial network idle
    try:
        await page.wait_for_load_state("networkidle", timeout=10000)
    except Exception:
        pass  # Continue even if timeout

    # Content selectors to try
    content_selectors = [
        "article",
        "main",
        "[role='main']",
        ".post-content",
        ".entry-content",
        ".article-content",
        "body"
    ]

    # Use adaptive strategy
    scraper = AdaptiveContentScraper()
    content, attempts, metadata = await scraper.scrape_with_adaptive_wait(
        page,
        content_selectors
    )

    return {
        'content': content,
        'content_length': len(content),
        'attempts': attempts,
        'strategy': metadata['strategy_level'],
        'total_wait_ms': metadata['total_extra_wait_ms'],
        'success': metadata['success']
    }


# Configuration examples

# Conservative (fast but may miss some content)
FAST_STRATEGY = WaitStrategy(
    min_content_threshold=100,
    initial_wait_ms=0,
    max_attempts=2,
    wait_increment_ms=1000,
    max_total_wait_ms=5000,
    enable_scroll=False,
    enable_cookie_click=True
)

# Balanced (recommended default)
BALANCED_STRATEGY = WaitStrategy(
    min_content_threshold=100,
    initial_wait_ms=0,
    max_attempts=4,
    wait_increment_ms=2000,
    max_total_wait_ms=15000,
    enable_scroll=True,
    enable_cookie_click=True
)

# Aggressive (thorough but slower)
THOROUGH_STRATEGY = WaitStrategy(
    min_content_threshold=100,
    initial_wait_ms=0,
    max_attempts=6,
    wait_increment_ms=3000,
    max_total_wait_ms=30000,
    enable_scroll=True,
    enable_cookie_click=True
)


if __name__ == "__main__":
    print("Adaptive Wait Strategy Configurations:")
    print()
    print("FAST_STRATEGY:")
    print(f"  Max attempts: {FAST_STRATEGY.max_attempts}")
    print(f"  Max wait: {FAST_STRATEGY.max_total_wait_ms/1000}s")
    print(f"  Scroll enabled: {FAST_STRATEGY.enable_scroll}")
    print()
    print("BALANCED_STRATEGY (recommended):")
    print(f"  Max attempts: {BALANCED_STRATEGY.max_attempts}")
    print(f"  Max wait: {BALANCED_STRATEGY.max_total_wait_ms/1000}s")
    print(f"  Scroll enabled: {BALANCED_STRATEGY.enable_scroll}")
    print()
    print("THOROUGH_STRATEGY:")
    print(f"  Max attempts: {THOROUGH_STRATEGY.max_attempts}")
    print(f"  Max wait: {THOROUGH_STRATEGY.max_total_wait_ms/1000}s")
    print(f"  Scroll enabled: {THOROUGH_STRATEGY.enable_scroll}")
