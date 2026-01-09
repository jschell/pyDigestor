"""
Playwright Web Scraping POC with Adaptive Wait Strategy

Uses progressive backoff instead of hardcoded per-site wait times.
Automatically adjusts to site behavior without configuration.
"""

import asyncio
import time
from typing import Optional
from dataclasses import dataclass

from playwright.async_api import async_playwright, Page, Browser

# Import our adaptive strategy
import sys
sys.path.insert(0, '/home/user/pyDigestor/poc')
from adaptive_wait_strategy import AdaptiveContentScraper, WaitStrategy, BALANCED_STRATEGY


@dataclass
class AdaptiveScrapingResult:
    """Result of an adaptive scraping attempt"""
    url: str
    success: bool
    content_length: int = 0
    title: Optional[str] = None
    error: Optional[str] = None
    duration_ms: float = 0
    attempts_needed: int = 1
    strategy_used: str = "basic"
    total_extra_wait_ms: int = 0


class AdaptivePlaywrightPOC:
    """POC using adaptive wait strategy instead of hardcoded delays"""

    TARGET_URLS = [
        "https://webdecoy.com/blog/ja4-fingerprinting-ai-scrapers-practical-guide/",
        "https://randywestergren.com/vibe-hacking-proxying-flutter-traffic-on-android-with-claude/",
        "https://www.group-ib.com/blog/ghost-tapped-chinese-malware/",
        "https://www.nsb.gov.tw/en/#/%E5%85%AC%E5%91%8A%E8%B3%87%E8%A8%8A/%E6%96%B0%E8%81%9E%E7%A8%BF%E6%9A%A8%E6%96%B0%E8%81%9E%E5%8F%83%E8%80%83%E8%B3%87%E6%96%99/2026-01-04/Analysis%20on%20China%E2%80%99s%20Cyber%20Threats%20to%20Taiwan%E2%80%99s%20Critical%20Infrastructure%20in%202025",
        "https://www.schneier.com/blog/archives/2026/01/ai-humans-making-the-relationship-work.html",
        "https://www.schneier.com/blog/archives/2026/01/telegram-hosting-worlds-largest-darknet-market.html",
    ]

    def __init__(self, wait_strategy: Optional[WaitStrategy] = None):
        self.results: list[AdaptiveScrapingResult] = []
        self.wait_strategy = wait_strategy or BALANCED_STRATEGY
        self.scraper = AdaptiveContentScraper(self.wait_strategy)

    async def scrape_url(self, page: Page, url: str) -> AdaptiveScrapingResult:
        """Scrape a URL with adaptive wait strategy"""
        start_time = time.time()
        result = AdaptiveScrapingResult(url=url, success=False)

        try:
            # Navigate to page
            print(f"\n  Loading {url[:60]}...")
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)

            # Initial network idle wait
            try:
                await page.wait_for_load_state("networkidle", timeout=10000)
            except Exception:
                pass

            # Get title
            result.title = await page.title()

            # Content selectors
            content_selectors = [
                "article",
                "main",
                "[role='main']",
                ".post-content",
                ".entry-content",
                ".article-content",
                "body"
            ]

            # Use adaptive strategy to get content
            content, attempts, metadata = await self.scraper.scrape_with_adaptive_wait(
                page,
                content_selectors
            )

            result.content_length = len(content)
            result.attempts_needed = attempts
            result.strategy_used = metadata['strategy_level']
            result.total_extra_wait_ms = metadata['total_extra_wait_ms']
            result.success = metadata['success']

            if not result.success:
                result.error = f"Insufficient content after {attempts} attempts"

        except Exception as e:
            result.error = str(e)

        result.duration_ms = (time.time() - start_time) * 1000
        return result

    async def run_poc(self):
        """Run POC with adaptive strategy on all URLs"""
        print("=" * 80)
        print("Playwright POC with Adaptive Wait Strategy")
        print("=" * 80)
        print()
        print("Strategy Configuration:")
        print(f"  Max attempts: {self.wait_strategy.max_attempts}")
        print(f"  Wait increment: {self.wait_strategy.wait_increment_ms/1000}s")
        print(f"  Max total wait: {self.wait_strategy.max_total_wait_ms/1000}s")
        print(f"  Content threshold: {self.wait_strategy.min_content_threshold} chars")
        print()

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()

            try:
                for url in self.TARGET_URLS:
                    print(f"\n{'='*80}")
                    print(f"Testing: {self._get_short_name(url)}")
                    print(f"{'='*80}")

                    result = await self.scrape_url(page, url)
                    self.results.append(result)
                    self.print_result(result)

            finally:
                await browser.close()

    def _get_short_name(self, url: str) -> str:
        """Get short display name for URL"""
        if "webdecoy.com" in url:
            return "webdecoy.com"
        elif "randywestergren.com" in url:
            return "randywestergren.com"
        elif "group-ib.com" in url:
            return "group-ib.com"
        elif "nsb.gov.tw" in url:
            return "nsb.gov.tw (Taiwan NSB)"
        elif "schneier.com" in url and "ai-humans" in url:
            return "schneier.com (AI/Humans)"
        elif "schneier.com" in url and "telegram" in url:
            return "schneier.com (Telegram)"
        else:
            return url[:50] + "..."

    def print_result(self, result: AdaptiveScrapingResult):
        """Print result of scraping attempt"""
        status = "✓ SUCCESS" if result.success else "✗ FAILED"
        print(f"\n  {status}")
        print(f"  Title: {result.title or 'N/A'}")
        print(f"  Content: {result.content_length:,} chars")
        print(f"  Duration: {result.duration_ms/1000:.2f}s")
        print(f"  Attempts: {result.attempts_needed}")
        print(f"  Strategy: {result.strategy_used}")
        if result.total_extra_wait_ms > 0:
            print(f"  Extra wait: +{result.total_extra_wait_ms/1000:.1f}s")
        if result.error:
            print(f"  Error: {result.error}")

    def print_summary(self):
        """Print comprehensive summary"""
        print("\n" + "=" * 80)
        print("SUMMARY")
        print("=" * 80)
        print()

        total = len(self.results)
        successful = sum(1 for r in self.results if r.success)

        print(f"Total URLs: {total}")
        print(f"Successful: {successful}")
        print(f"Failed: {total - successful}")
        print(f"Success Rate: {(successful/total*100):.1f}%")
        print()

        # Adaptive strategy effectiveness
        print("Adaptive Strategy Effectiveness:")
        print("-" * 80)
        print(f"{'URL':<35} {'Attempts':<10} {'Strategy':<20} {'Time':<10}")
        print("-" * 80)

        for result in self.results:
            short_name = self._get_short_name(result.url)
            time_str = f"{result.duration_ms/1000:.2f}s"
            marker = "✓" if result.success else "✗"
            print(f"{marker} {short_name:<33} {result.attempts_needed:<10} "
                  f"{result.strategy_used:<20} {time_str:<10}")

        print()

        # Attempt distribution
        attempt_counts = {}
        for result in self.results:
            if result.success:
                attempt_counts[result.attempts_needed] = attempt_counts.get(result.attempts_needed, 0) + 1

        if attempt_counts:
            print("Content found on attempt:")
            for attempt in sorted(attempt_counts.keys()):
                count = attempt_counts[attempt]
                print(f"  Attempt {attempt}: {count} URL{'s' if count != 1 else ''}")
            print()

        # Performance analysis
        basic_results = [r for r in self.results if r.success and r.attempts_needed == 1]
        enhanced_results = [r for r in self.results if r.success and r.attempts_needed > 1]

        if basic_results:
            avg_basic = sum(r.duration_ms for r in basic_results) / len(basic_results)
            print(f"Average time (1 attempt): {avg_basic/1000:.2f}s ({len(basic_results)} URLs)")

        if enhanced_results:
            avg_enhanced = sum(r.duration_ms for r in enhanced_results) / len(enhanced_results)
            avg_attempts = sum(r.attempts_needed for r in enhanced_results) / len(enhanced_results)
            print(f"Average time (multi-attempt): {avg_enhanced/1000:.2f}s "
                  f"({len(enhanced_results)} URLs, avg {avg_attempts:.1f} attempts)")

        print()
        print("=" * 80)
        print("BENEFITS OF ADAPTIVE STRATEGY")
        print("=" * 80)
        print()
        print("✓ No hardcoded per-site configuration needed")
        print("✓ Automatically adapts to site behavior")
        print("✓ Fast path for responsive sites (no wasted time)")
        print("✓ Progressive backoff for slow sites")
        print("✓ Self-tuning based on content retrieval")
        print()

        if enhanced_results:
            print("Sites that needed enhanced strategy:")
            for result in enhanced_results:
                short_name = self._get_short_name(result.url)
                print(f"  - {short_name}: {result.attempts_needed} attempts, "
                      f"+{result.total_extra_wait_ms/1000:.1f}s extra wait")
        else:
            print("All sites worked with basic strategy (1 attempt)!")


async def main():
    """Run the adaptive POC"""
    # You can easily switch strategies
    # poc = AdaptivePlaywrightPOC(FAST_STRATEGY)
    poc = AdaptivePlaywrightPOC(BALANCED_STRATEGY)
    # poc = AdaptivePlaywrightPOC(THOROUGH_STRATEGY)

    await poc.run_poc()
    poc.print_summary()


if __name__ == "__main__":
    asyncio.run(main())
