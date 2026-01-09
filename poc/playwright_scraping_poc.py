"""
Playwright Web Scraping POC

Tests minimal requirements for scraping content from various websites.
This POC explores different approaches:
1. Headless vs headed mode
2. Different browser types (Chromium, Firefox, WebKit)
3. Wait strategies
4. JavaScript execution requirements
"""

import asyncio
import time
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, field

from playwright.async_api import async_playwright, Page, Browser, BrowserContext


@dataclass
class ScrapingResult:
    """Result of a scraping attempt"""
    url: str
    success: bool
    content_length: int = 0
    title: Optional[str] = None
    error: Optional[str] = None
    duration_ms: float = 0
    method: str = ""
    has_javascript: bool = False
    main_content_preview: str = ""


@dataclass
class ScrapingConfig:
    """Configuration for scraping attempt"""
    headless: bool = True
    browser_type: str = "chromium"  # chromium, firefox, webkit
    wait_for_selector: Optional[str] = None
    wait_timeout: int = 10000  # milliseconds
    viewport_width: int = 1920
    viewport_height: int = 1080
    user_agent: Optional[str] = None
    extra_http_headers: Dict[str, str] = field(default_factory=dict)


class PlaywrightScrapingPOC:
    """POC for testing Playwright scraping capabilities"""

    TARGET_URLS = [
        # Original test URLs
        "https://webdecoy.com/blog/ja4-fingerprinting-ai-scrapers-practical-guide/",
        "https://randywestergren.com/vibe-hacking-proxying-flutter-traffic-on-android-with-claude/",
        "https://www.group-ib.com/blog/ghost-tapped-chinese-malware/",
        # Additional test URLs
        "https://www.nsb.gov.tw/en/#/%E5%85%AC%E5%91%8A%E8%B3%87%E8%A8%8A/%E6%96%B0%E8%81%9E%E7%A8%BF%E6%9A%A8%E6%96%B0%E8%81%9E%E5%8F%83%E8%80%83%E8%B3%87%E6%96%99/2026-01-04/Analysis%20on%20China%E2%80%99s%20Cyber%20Threats%20to%20Taiwan%E2%80%99s%20Critical%20Infrastructure%20in%202025",
        "https://www.schneier.com/blog/archives/2026/01/ai-humans-making-the-relationship-work.html",
        "https://www.schneier.com/blog/archives/2026/01/telegram-hosting-worlds-largest-darknet-market.html",
    ]

    def __init__(self):
        self.results: List[ScrapingResult] = []

    async def scrape_page(
        self,
        url: str,
        config: ScrapingConfig,
        page: Page
    ) -> ScrapingResult:
        """Scrape a single page with given configuration"""
        start_time = time.time()
        result = ScrapingResult(
            url=url,
            success=False,
            method=f"{config.browser_type}_headless={config.headless}"
        )

        try:
            # Navigate to the page
            response = await page.goto(url, wait_until="domcontentloaded", timeout=config.wait_timeout)

            if response is None:
                result.error = "No response received"
                return result

            # Wait for specific selector if provided
            if config.wait_for_selector:
                await page.wait_for_selector(config.wait_for_selector, timeout=config.wait_timeout)
            else:
                # Wait for network to be idle
                await page.wait_for_load_state("networkidle", timeout=config.wait_timeout)

            # Get page title
            result.title = await page.title()

            # Get main content
            # Try different selectors commonly used for blog content
            content_selectors = [
                "article",
                "main",
                "[role='main']",
                ".post-content",
                ".entry-content",
                ".article-content",
                "body"
            ]

            content = ""
            for selector in content_selectors:
                try:
                    element = await page.query_selector(selector)
                    if element:
                        content = await element.inner_text()
                        if len(content.strip()) > 100:  # Found substantial content
                            break
                except Exception:
                    continue

            result.content_length = len(content)
            result.main_content_preview = content[:500].strip() if content else ""

            # Check if page has significant JavaScript
            scripts = await page.query_selector_all("script")
            result.has_javascript = len(scripts) > 5  # Arbitrary threshold

            result.success = result.content_length > 100
            result.duration_ms = (time.time() - start_time) * 1000

            if not result.success:
                result.error = f"Insufficient content retrieved ({result.content_length} chars)"

        except Exception as e:
            result.error = str(e)
            result.duration_ms = (time.time() - start_time) * 1000

        return result

    async def test_url_with_config(
        self,
        url: str,
        config: ScrapingConfig,
        browser: Browser
    ) -> ScrapingResult:
        """Test a URL with a specific configuration"""
        context_options = {
            "viewport": {"width": config.viewport_width, "height": config.viewport_height},
        }

        if config.user_agent:
            context_options["user_agent"] = config.user_agent

        if config.extra_http_headers:
            context_options["extra_http_headers"] = config.extra_http_headers

        context: BrowserContext = await browser.new_context(**context_options)
        page = await context.new_page()

        try:
            result = await self.scrape_page(url, config, page)
            return result
        finally:
            await context.close()

    async def run_poc_tests(self):
        """Run POC tests with various configurations"""
        async with async_playwright() as p:
            print("=" * 80)
            print("Playwright Web Scraping POC")
            print("=" * 80)
            print()

            # Test configurations
            configs = [
                ScrapingConfig(
                    headless=True,
                    browser_type="chromium",
                ),
                ScrapingConfig(
                    headless=False,
                    browser_type="chromium",
                ),
                ScrapingConfig(
                    headless=True,
                    browser_type="firefox",
                ),
            ]

            for config in configs:
                print(f"\n{'='*80}")
                print(f"Testing with: {config.browser_type}, Headless: {config.headless}")
                print(f"{'='*80}\n")

                # Launch browser
                if config.browser_type == "chromium":
                    browser = await p.chromium.launch(headless=config.headless)
                elif config.browser_type == "firefox":
                    browser = await p.firefox.launch(headless=config.headless)
                elif config.browser_type == "webkit":
                    browser = await p.webkit.launch(headless=config.headless)
                else:
                    print(f"Unknown browser type: {config.browser_type}")
                    continue

                try:
                    for url in self.TARGET_URLS:
                        print(f"\nTesting: {url}")
                        result = await self.test_url_with_config(url, config, browser)
                        self.results.append(result)
                        self.print_result(result)
                finally:
                    await browser.close()

    def print_result(self, result: ScrapingResult):
        """Print a scraping result"""
        status = "✓ SUCCESS" if result.success else "✗ FAILED"
        print(f"  Status: {status}")
        print(f"  Title: {result.title or 'N/A'}")
        print(f"  Content Length: {result.content_length} chars")
        print(f"  Duration: {result.duration_ms:.2f}ms")
        print(f"  Has JavaScript: {result.has_javascript}")

        if result.error:
            print(f"  Error: {result.error}")

        if result.main_content_preview:
            preview = result.main_content_preview.replace('\n', ' ')[:200]
            print(f"  Preview: {preview}...")

    def print_summary(self):
        """Print summary of all results"""
        print("\n" + "=" * 80)
        print("SUMMARY")
        print("=" * 80)
        print()

        total = len(self.results)
        successful = sum(1 for r in self.results if r.success)

        print(f"Total Tests: {total}")
        print(f"Successful: {successful}")
        print(f"Failed: {total - successful}")
        print(f"Success Rate: {(successful/total*100):.1f}%" if total > 0 else "N/A")
        print()

        # Group by URL
        print("Results by URL:")
        print("-" * 80)
        for url in self.TARGET_URLS:
            url_results = [r for r in self.results if r.url == url]
            successful_configs = [r.method for r in url_results if r.success]
            print(f"\n{url}")
            print(f"  Success rate: {len(successful_configs)}/{len(url_results)}")
            if successful_configs:
                print(f"  Working configs: {', '.join(successful_configs)}")
            else:
                print(f"  No working configs found")
                # Print errors
                for r in url_results:
                    if r.error:
                        print(f"    - {r.method}: {r.error[:100]}")

        print("\n" + "=" * 80)
        print("MINIMAL REQUIREMENTS")
        print("=" * 80)
        print()

        # Analyze minimal requirements
        if successful:
            headless_success = any(r.success and "headless=True" in r.method for r in self.results)
            chromium_success = any(r.success and "chromium" in r.method for r in self.results)
            firefox_success = any(r.success and "firefox" in r.method for r in self.results)

            print(f"✓ Headless mode works: {'Yes' if headless_success else 'No'}")
            print(f"✓ Chromium works: {'Yes' if chromium_success else 'No'}")
            print(f"✓ Firefox works: {'Yes' if firefox_success else 'No'}")
            print()
            print("Recommended minimal setup:")
            if headless_success:
                print("  - Use headless mode (saves resources)")
            if chromium_success:
                print("  - Chromium browser is sufficient")
            print("  - Wait for 'networkidle' state")
            print("  - No special user agent required")
        else:
            print("⚠ No successful scraping attempts. May need:")
            print("  - Custom user agent")
            print("  - Stealth plugins")
            print("  - Cookie acceptance automation")
            print("  - Longer wait times")


async def main():
    """Run the POC"""
    poc = PlaywrightScrapingPOC()
    await poc.run_poc_tests()
    poc.print_summary()


if __name__ == "__main__":
    asyncio.run(main())
