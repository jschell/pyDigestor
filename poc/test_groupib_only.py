"""
Quick test script specifically for group-ib.com with enhanced wait times.

Tests the one failing URL with additional strategies.
"""

import asyncio
import time
from typing import Optional
from dataclasses import dataclass

from playwright.async_api import async_playwright, Page


@dataclass
class GroupIBTestResult:
    """Test result for group-ib.com"""
    strategy: str
    success: bool
    content_length: int = 0
    title: Optional[str] = None
    error: Optional[str] = None
    duration_ms: float = 0
    content_preview: str = ""


class GroupIBTest:
    """Focused test for group-ib.com"""

    URL = "https://www.group-ib.com/blog/ghost-tapped-chinese-malware/"

    def __init__(self):
        self.results: list[GroupIBTestResult] = []

    async def test_basic(self, page: Page) -> GroupIBTestResult:
        """Basic approach (baseline)"""
        start_time = time.time()
        result = GroupIBTestResult(strategy="basic", success=False)

        try:
            await page.goto(self.URL, wait_until="networkidle", timeout=30000)
            result.title = await page.title()

            element = await page.query_selector("article, main, body")
            if element:
                content = await element.inner_text()
                result.content_length = len(content)
                result.content_preview = content[:200]
                result.success = result.content_length > 100

        except Exception as e:
            result.error = str(e)

        result.duration_ms = (time.time() - start_time) * 1000
        return result

    async def test_with_longer_wait(self, page: Page) -> GroupIBTestResult:
        """With 5 second additional wait"""
        start_time = time.time()
        result = GroupIBTestResult(strategy="longer_wait_5s", success=False)

        try:
            await page.goto(self.URL, wait_until="networkidle", timeout=30000)

            # Additional wait
            print("  Waiting 5 additional seconds...")
            await page.wait_for_timeout(5000)

            result.title = await page.title()

            element = await page.query_selector("article, main, body")
            if element:
                content = await element.inner_text()
                result.content_length = len(content)
                result.content_preview = content[:200]
                result.success = result.content_length > 100

        except Exception as e:
            result.error = str(e)

        result.duration_ms = (time.time() - start_time) * 1000
        return result

    async def test_with_scroll(self, page: Page) -> GroupIBTestResult:
        """With scrolling to trigger lazy loading"""
        start_time = time.time()
        result = GroupIBTestResult(strategy="scroll_lazy_load", success=False)

        try:
            await page.goto(self.URL, wait_until="networkidle", timeout=30000)

            print("  Scrolling to trigger lazy loading...")
            await page.evaluate('window.scrollTo(0, document.body.scrollHeight / 2)')
            await page.wait_for_timeout(2000)
            await page.evaluate('window.scrollTo(0, 0)')
            await page.wait_for_timeout(1000)

            result.title = await page.title()

            element = await page.query_selector("article, main, body")
            if element:
                content = await element.inner_text()
                result.content_length = len(content)
                result.content_preview = content[:200]
                result.success = result.content_length > 100

        except Exception as e:
            result.error = str(e)

        result.duration_ms = (time.time() - start_time) * 1000
        return result

    async def test_with_cookies_and_wait(self, page: Page) -> GroupIBTestResult:
        """With cookie handling and longer wait"""
        start_time = time.time()
        result = GroupIBTestResult(strategy="cookies_plus_wait", success=False)

        try:
            await page.goto(self.URL, wait_until="networkidle", timeout=30000)

            # Try cookie consent
            print("  Looking for cookie consent...")
            try:
                await page.click('button:has-text("Accept"), button:has-text("OK")', timeout=2000)
                print("  ✓ Clicked cookie button")
                await page.wait_for_timeout(1000)
            except Exception:
                print("  No cookie button found")

            # Wait longer
            print("  Waiting 5 additional seconds...")
            await page.wait_for_timeout(5000)

            result.title = await page.title()

            element = await page.query_selector("article, main, body")
            if element:
                content = await element.inner_text()
                result.content_length = len(content)
                result.content_preview = content[:200]
                result.success = result.content_length > 100

        except Exception as e:
            result.error = str(e)

        result.duration_ms = (time.time() - start_time) * 1000
        return result

    async def test_comprehensive(self, page: Page) -> GroupIBTestResult:
        """Comprehensive approach: cookies + wait + scroll"""
        start_time = time.time()
        result = GroupIBTestResult(strategy="comprehensive", success=False)

        try:
            print("  Loading page...")
            await page.goto(self.URL, wait_until="networkidle", timeout=30000)

            # Cookie consent
            print("  Checking for cookie consent...")
            try:
                await page.click('button:has-text("Accept"), button:has-text("OK"), [class*="cookie"] button', timeout=2000)
                print("  ✓ Clicked cookie button")
                await page.wait_for_timeout(1000)
            except Exception:
                print("  No cookie button found")

            # Wait for lazy loading
            print("  Waiting 5 seconds for lazy-loaded content...")
            await page.wait_for_timeout(5000)

            # Scroll
            print("  Scrolling to trigger lazy loading...")
            await page.evaluate('window.scrollTo(0, document.body.scrollHeight / 2)')
            await page.wait_for_timeout(2000)
            await page.evaluate('window.scrollTo(0, 0)')
            await page.wait_for_timeout(1000)

            # Final network idle wait
            print("  Waiting for final network idle...")
            try:
                await page.wait_for_load_state("networkidle", timeout=10000)
            except Exception:
                pass

            result.title = await page.title()
            print(f"  Title: {result.title}")

            # Try multiple selectors
            for selector in ['article', 'main', '[role="main"]', '.post-content', 'body']:
                element = await page.query_selector(selector)
                if element:
                    content = await element.inner_text()
                    print(f"  Selector '{selector}': {len(content)} chars")
                    if len(content) > result.content_length:
                        result.content_length = len(content)
                        result.content_preview = content[:200]
                        result.success = result.content_length > 100

        except Exception as e:
            result.error = str(e)

        result.duration_ms = (time.time() - start_time) * 1000
        return result

    async def test_with_screenshot(self, page: Page) -> GroupIBTestResult:
        """With screenshot capture for debugging"""
        start_time = time.time()
        result = GroupIBTestResult(strategy="debug_screenshot", success=False)

        try:
            print("  Loading page...")
            await page.goto(self.URL, wait_until="networkidle", timeout=30000)

            # Save initial state
            await page.screenshot(path="/home/user/pyDigestor/poc/groupib_initial.png")
            print("  📸 Saved: groupib_initial.png")

            # Cookie + wait + scroll
            try:
                await page.click('button:has-text("Accept"), button:has-text("OK")', timeout=2000)
                await page.wait_for_timeout(1000)
                await page.screenshot(path="/home/user/pyDigestor/poc/groupib_after_cookie.png")
                print("  📸 Saved: groupib_after_cookie.png")
            except Exception:
                pass

            await page.wait_for_timeout(5000)

            await page.evaluate('window.scrollTo(0, document.body.scrollHeight / 2)')
            await page.wait_for_timeout(2000)
            await page.screenshot(path="/home/user/pyDigestor/poc/groupib_after_scroll.png")
            print("  📸 Saved: groupib_after_scroll.png")

            await page.evaluate('window.scrollTo(0, 0)')
            await page.wait_for_timeout(1000)

            # Save HTML
            html = await page.content()
            with open("/home/user/pyDigestor/poc/groupib_page.html", "w") as f:
                f.write(html)
            print("  💾 Saved: groupib_page.html")

            result.title = await page.title()

            element = await page.query_selector("article, main, body")
            if element:
                content = await element.inner_text()
                result.content_length = len(content)
                result.content_preview = content[:200]
                result.success = result.content_length > 100

        except Exception as e:
            result.error = str(e)

        result.duration_ms = (time.time() - start_time) * 1000
        return result

    async def run_tests(self):
        """Run all test strategies"""
        print("=" * 80)
        print("Group-IB Test Suite - Enhanced Wait Times")
        print("=" * 80)
        print(f"\nTarget: {self.URL}\n")

        strategies = [
            ("1. Basic (baseline)", self.test_basic),
            ("2. Longer Wait (5s)", self.test_with_longer_wait),
            ("3. Scroll Lazy Load", self.test_with_scroll),
            ("4. Cookies + Wait", self.test_with_cookies_and_wait),
            ("5. Comprehensive (All)", self.test_comprehensive),
            ("6. Debug + Screenshot", self.test_with_screenshot),
        ]

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)

            for strategy_name, strategy_func in strategies:
                print(f"\n{'='*80}")
                print(f"Strategy: {strategy_name}")
                print(f"{'='*80}")

                page = await browser.new_page()
                try:
                    result = await strategy_func(page)
                    self.results.append(result)
                    self.print_result(result)
                finally:
                    await page.close()

            await browser.close()

    def print_result(self, result: GroupIBTestResult):
        """Print result"""
        print(f"\n  {'='*76}")
        status = "✓ SUCCESS" if result.success else "✗ FAILED"
        print(f"  {status}")
        print(f"  Duration: {result.duration_ms:.2f}ms")
        print(f"  Content: {result.content_length:,} chars")
        if result.title:
            print(f"  Title: {result.title[:60]}...")
        if result.error:
            print(f"  Error: {result.error[:70]}")
        if result.content_preview:
            preview = result.content_preview.replace('\n', ' ')[:100]
            print(f"  Preview: {preview}...")

    def print_summary(self):
        """Print final summary"""
        print("\n" + "=" * 80)
        print("FINAL SUMMARY")
        print("=" * 80)
        print()

        successful = [r for r in self.results if r.success]
        failed = [r for r in self.results if not r.success]

        print(f"Total strategies tested: {len(self.results)}")
        print(f"Successful: {len(successful)}")
        print(f"Failed: {len(failed)}")
        print()

        print("Results:")
        print("-" * 80)
        for result in self.results:
            status = "✓" if result.success else "✗"
            print(f"{status} {result.strategy:25} | {result.content_length:8,} chars | {result.duration_ms:8.1f}ms")

        print("\n" + "=" * 80)
        print("ANALYSIS")
        print("=" * 80)
        print()

        if successful:
            print("✓ Working strategies found!")
            print()
            for r in successful:
                print(f"  Strategy: {r.strategy}")
                print(f"    - Content: {r.content_length:,} chars")
                print(f"    - Duration: {r.duration_ms:.1f}ms")
                print()

            fastest = min(successful, key=lambda x: x.duration_ms)
            print(f"💡 Recommended: Use '{fastest.strategy}' strategy")
            print(f"   ({fastest.content_length:,} chars in {fastest.duration_ms:.1f}ms)")
        else:
            print("✗ All strategies failed")
            print()
            print("The site likely has one of the following issues:")
            print("  1. Geographic restrictions (blocks non-EU/US traffic)")
            print("  2. Advanced bot detection (Cloudflare, Imperva)")
            print("  3. Requires authentication")
            print("  4. JavaScript errors preventing content load")
            print("  5. Content behind CAPTCHA")
            print()
            print("Check the saved files:")
            print("  - groupib_*.png screenshots")
            print("  - groupib_page.html HTML source")


async def main():
    """Run the test"""
    tester = GroupIBTest()
    await tester.run_tests()
    tester.print_summary()


if __name__ == "__main__":
    asyncio.run(main())
