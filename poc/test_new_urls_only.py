"""
Quick test script for the new URLs only.

Tests only the 3 newly added URLs with minimal configurations
to quickly assess if they work with Playwright.
"""

import asyncio
import time
from typing import Optional
from dataclasses import dataclass

from playwright.async_api import async_playwright, Page


@dataclass
class QuickTestResult:
    """Quick test result"""
    url: str
    url_name: str
    success: bool
    content_length: int = 0
    title: Optional[str] = None
    error: Optional[str] = None
    duration_ms: float = 0


class NewURLQuickTest:
    """Quick test for new URLs"""

    NEW_URLS = {
        "Taiwan NSB": "https://www.nsb.gov.tw/en/#/%E5%85%AC%E5%91%8A%E8%B3%87%E8%A8%8A/%E6%96%B0%E8%81%9E%E7%A8%BF%E6%9A%A8%E6%96%B0%E8%81%9E%E5%8F%83%E8%80%83%E8%B3%87%E6%96%99/2026-01-04/Analysis%20on%20China%E2%80%99s%20Cyber%20Threats%20to%20Taiwan%E2%80%99s%20Critical%20Infrastructure%20in%202025",
        "Schneier - AI/Humans": "https://www.schneier.com/blog/archives/2026/01/ai-humans-making-the-relationship-work.html",
        "Schneier - Telegram": "https://www.schneier.com/blog/archives/2026/01/telegram-hosting-worlds-largest-darknet-market.html",
    }

    def __init__(self):
        self.results: list[QuickTestResult] = []

    async def test_url(self, page: Page, url_name: str, url: str) -> QuickTestResult:
        """Test a single URL"""
        start_time = time.time()
        result = QuickTestResult(url=url, url_name=url_name, success=False)

        try:
            print(f"\n  Loading page...")
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)

            # For hash-based routing (like Taiwan NSB), give extra time
            if "#/" in url:
                print(f"  Detected hash routing, waiting for SPA to initialize...")
                await page.wait_for_timeout(2000)

            print(f"  Waiting for network idle...")
            await page.wait_for_load_state("networkidle", timeout=30000)

            # Get title
            result.title = await page.title()
            print(f"  Title: {result.title}")

            # Try to find content
            content = ""
            selectors_tried = []

            for selector in ['article', 'main', '[role="main"]', '.post-content', '.entry-content', 'body']:
                element = await page.query_selector(selector)
                if element:
                    text = await element.inner_text()
                    selectors_tried.append(f"{selector}: {len(text)} chars")
                    if len(text.strip()) > 100 and len(text) > len(content):
                        content = text

            print(f"  Content extraction attempts:")
            for attempt in selectors_tried:
                print(f"    - {attempt}")

            result.content_length = len(content)
            result.success = result.content_length > 100

            if result.success:
                preview = content[:200].replace('\n', ' ')
                print(f"  Preview: {preview}...")
            else:
                print(f"  ⚠ Warning: Insufficient content ({result.content_length} chars)")

        except Exception as e:
            result.error = str(e)
            print(f"  ✗ Error: {e}")

        result.duration_ms = (time.time() - start_time) * 1000
        return result

    async def run_tests(self):
        """Run quick tests on new URLs"""
        print("=" * 80)
        print("Quick Test: New URLs Only")
        print("=" * 80)
        print(f"\nTesting {len(self.NEW_URLS)} new URLs with Chromium headless...\n")

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()

            try:
                for url_name, url in self.NEW_URLS.items():
                    print(f"\n{'='*80}")
                    print(f"Testing: {url_name}")
                    print(f"{'='*80}")
                    print(f"URL: {url[:80]}{'...' if len(url) > 80 else ''}")

                    result = await self.test_url(page, url_name, url)
                    self.results.append(result)
                    self.print_result_summary(result)

            finally:
                await browser.close()

    def print_result_summary(self, result: QuickTestResult):
        """Print summary of result"""
        print(f"\n  {'='*76}")
        status = "✓ SUCCESS" if result.success else "✗ FAILED"
        print(f"  {status}")
        print(f"  Duration: {result.duration_ms:.2f}ms")
        print(f"  Content: {result.content_length} chars")
        if result.error:
            print(f"  Error: {result.error}")

    def print_final_summary(self):
        """Print final summary"""
        print("\n" + "=" * 80)
        print("FINAL SUMMARY")
        print("=" * 80)
        print()

        total = len(self.results)
        successful = sum(1 for r in self.results if r.success)
        failed = total - successful

        print(f"Total URLs tested: {total}")
        print(f"Successful: {successful} ({successful/total*100:.1f}%)")
        print(f"Failed: {failed} ({failed/total*100:.1f}%)")
        print()

        print("Results:")
        print("-" * 80)
        for result in self.results:
            status = "✓" if result.success else "✗"
            print(f"{status} {result.url_name:25} | {result.content_length:7,} chars | {result.duration_ms:8.1f}ms")
            if result.title:
                title_short = result.title[:60] + "..." if len(result.title) > 60 else result.title
                print(f"  Title: {title_short}")
            if result.error:
                print(f"  Error: {result.error[:70]}")

        print("\n" + "=" * 80)
        print("ANALYSIS")
        print("=" * 80)
        print()

        # Analyze by domain
        schneier_results = [r for r in self.results if 'schneier' in r.url.lower()]
        taiwan_results = [r for r in self.results if 'nsb.gov.tw' in r.url]

        if schneier_results:
            schneier_success = all(r.success for r in schneier_results)
            print(f"Schneier Blog (schneier.com):")
            if schneier_success:
                print(f"  ✓ Both URLs work perfectly ({len(schneier_results)}/2)")
                avg_time = sum(r.duration_ms for r in schneier_results) / len(schneier_results)
                print(f"  ✓ Average load time: {avg_time:.1f}ms")
                print(f"  ✓ Standard blog structure confirmed")
            else:
                print(f"  ✗ Some URLs failed ({sum(1 for r in schneier_results if r.success)}/2)")

        print()

        if taiwan_results:
            taiwan_result = taiwan_results[0]
            print(f"Taiwan NSB (nsb.gov.tw):")
            if taiwan_result.success:
                print(f"  ✓ Successfully scraped")
                print(f"  ✓ Hash-based routing handled correctly")
                print(f"  ✓ Load time: {taiwan_result.duration_ms:.1f}ms")
            else:
                print(f"  ✗ Failed to scrape")
                if taiwan_result.error:
                    print(f"  ⚠ Error: {taiwan_result.error}")
                if taiwan_result.content_length == 0:
                    print(f"  ⚠ No content retrieved - possible issues:")
                    print(f"     - Hash routing not working")
                    print(f"     - Geographic restrictions")
                    print(f"     - Requires authentication")
                    print(f"     - Content loaded after longer delay")
                else:
                    print(f"  ⚠ Insufficient content ({taiwan_result.content_length} chars)")

        print("\n" + "=" * 80)
        print("RECOMMENDATIONS")
        print("=" * 80)
        print()

        if successful == total:
            print("✓ All new URLs work with basic Playwright setup!")
            print("  → Add these to production scraping pipeline")
            print("  → No special handling needed")
        elif successful > 0:
            print(f"✓ {successful}/{total} URLs work with basic Playwright setup")
            working = [r.url_name for r in self.results if r.success]
            failing = [r.url_name for r in self.results if not r.success]
            print(f"  Working: {', '.join(working)}")
            print(f"  Failing: {', '.join(failing)}")
            print(f"\n  → Add working URLs to production")
            print(f"  → Investigate failing URLs with enhanced POC")
        else:
            print("✗ All URLs failed with basic Playwright setup")
            print("  → Use enhanced POC with advanced strategies")
            print("  → Check geographic restrictions")
            print("  → Verify URLs are accessible from this location")


async def main():
    """Run quick tests"""
    tester = NewURLQuickTest()
    await tester.run_tests()
    tester.print_final_summary()


if __name__ == "__main__":
    asyncio.run(main())
