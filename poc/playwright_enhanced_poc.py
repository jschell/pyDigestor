"""
Enhanced Playwright Web Scraping POC

Tests advanced strategies for difficult-to-scrape websites.
Specifically targets group-ib.com which failed in the basic POC.
"""

import asyncio
import time
from typing import Optional
from dataclasses import dataclass

from playwright.async_api import async_playwright, Page


@dataclass
class EnhancedScrapingResult:
    """Result of an enhanced scraping attempt"""
    url: str
    success: bool
    strategy: str
    content_length: int = 0
    title: Optional[str] = None
    error: Optional[str] = None
    duration_ms: float = 0
    screenshot_path: Optional[str] = None
    html_saved: bool = False


class EnhancedPlaywrightPOC:
    """Enhanced POC testing various strategies for difficult websites"""

    TARGET_URL = "https://www.group-ib.com/blog/ghost-tapped-chinese-malware/"

    def __init__(self):
        self.results: list[EnhancedScrapingResult] = []

    async def strategy_basic(self, page: Page, url: str) -> EnhancedScrapingResult:
        """Strategy 1: Basic approach (baseline from original POC)"""
        start_time = time.time()
        result = EnhancedScrapingResult(url=url, success=False, strategy="basic")

        try:
            await page.goto(url, wait_until="networkidle", timeout=30000)

            content = ""
            for selector in ['article', 'main', '[role="main"]', 'body']:
                element = await page.query_selector(selector)
                if element:
                    content = await element.inner_text()
                    if len(content.strip()) > 100:
                        break

            result.title = await page.title()
            result.content_length = len(content)
            result.success = result.content_length > 100

        except Exception as e:
            result.error = str(e)

        result.duration_ms = (time.time() - start_time) * 1000
        return result

    async def strategy_with_cookies(self, page: Page, url: str) -> EnhancedScrapingResult:
        """Strategy 2: Handle cookie consent banners"""
        start_time = time.time()
        result = EnhancedScrapingResult(url=url, success=False, strategy="cookie_consent")

        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)

            # Try to find and click cookie consent buttons
            cookie_selectors = [
                'button:has-text("Accept")',
                'button:has-text("Agree")',
                'button:has-text("OK")',
                'button:has-text("Accept all")',
                'button:has-text("Accept cookies")',
                '[id*="accept"]',
                '[class*="accept"]',
                '[class*="cookie"] button',
                '.cookie-consent button',
            ]

            for selector in cookie_selectors:
                try:
                    await page.click(selector, timeout=2000)
                    print(f"  ✓ Clicked cookie button: {selector}")
                    await page.wait_for_timeout(1000)
                    break
                except:
                    continue

            # Wait for network to be idle after interaction
            await page.wait_for_load_state("networkidle", timeout=30000)

            content = ""
            for selector in ['article', 'main', '[role="main"]', '.post-content', 'body']:
                element = await page.query_selector(selector)
                if element:
                    content = await element.inner_text()
                    if len(content.strip()) > 100:
                        break

            result.title = await page.title()
            result.content_length = len(content)
            result.success = result.content_length > 100

        except Exception as e:
            result.error = str(e)

        result.duration_ms = (time.time() - start_time) * 1000
        return result

    async def strategy_with_scroll(self, page: Page, url: str) -> EnhancedScrapingResult:
        """Strategy 3: Scroll to trigger lazy loading"""
        start_time = time.time()
        result = EnhancedScrapingResult(url=url, success=False, strategy="scroll_lazy_load")

        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)

            # Handle cookies first
            try:
                await page.click('button:has-text("Accept")', timeout=2000)
                await page.wait_for_timeout(1000)
            except:
                pass

            # Scroll down the page in increments to trigger lazy loading
            viewport_height = page.viewport_size['height']
            total_height = await page.evaluate('document.body.scrollHeight')

            scroll_steps = min(5, int(total_height / viewport_height) + 1)
            for i in range(scroll_steps):
                await page.evaluate(f'window.scrollTo(0, {viewport_height * i})')
                await page.wait_for_timeout(500)

            # Scroll back to top
            await page.evaluate('window.scrollTo(0, 0)')
            await page.wait_for_timeout(500)

            # Wait for any remaining network activity
            await page.wait_for_load_state("networkidle", timeout=10000)

            content = ""
            for selector in ['article', 'main', '[role="main"]', '.post-content', 'body']:
                element = await page.query_selector(selector)
                if element:
                    content = await element.inner_text()
                    if len(content.strip()) > 100:
                        break

            result.title = await page.title()
            result.content_length = len(content)
            result.success = result.content_length > 100

        except Exception as e:
            result.error = str(e)

        result.duration_ms = (time.time() - start_time) * 1000
        return result

    async def strategy_wait_for_selector(self, page: Page, url: str) -> EnhancedScrapingResult:
        """Strategy 4: Wait for specific content selectors"""
        start_time = time.time()
        result = EnhancedScrapingResult(url=url, success=False, strategy="wait_for_selector")

        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)

            # Handle cookies
            try:
                await page.click('button:has-text("Accept")', timeout=2000)
                await page.wait_for_timeout(1000)
            except:
                pass

            # Wait for common blog content selectors
            content_found = False
            for selector in ['article', 'main', '.post-content', '[class*="content"]', '[class*="article"]']:
                try:
                    await page.wait_for_selector(selector, timeout=10000)
                    content_found = True
                    print(f"  ✓ Found content selector: {selector}")
                    break
                except:
                    continue

            if not content_found:
                result.error = "No content selectors found"

            # Additional wait for network
            await page.wait_for_load_state("networkidle", timeout=10000)

            content = ""
            for selector in ['article', 'main', '[role="main"]', '.post-content', 'body']:
                element = await page.query_selector(selector)
                if element:
                    content = await element.inner_text()
                    if len(content.strip()) > 100:
                        break

            result.title = await page.title()
            result.content_length = len(content)
            result.success = result.content_length > 100

        except Exception as e:
            result.error = str(e)

        result.duration_ms = (time.time() - start_time) * 1000
        return result

    async def strategy_longer_timeout(self, page: Page, url: str) -> EnhancedScrapingResult:
        """Strategy 5: Use much longer timeouts for slow sites"""
        start_time = time.time()
        result = EnhancedScrapingResult(url=url, success=False, strategy="longer_timeout")

        try:
            # Set longer default timeout
            page.set_default_timeout(60000)

            await page.goto(url, wait_until="domcontentloaded", timeout=60000)

            # Handle cookies
            try:
                await page.click('button:has-text("Accept")', timeout=5000)
                await page.wait_for_timeout(2000)
            except:
                pass

            # Wait longer for network idle
            await page.wait_for_load_state("networkidle", timeout=60000)

            # Additional wait just in case
            await page.wait_for_timeout(5000)

            content = ""
            for selector in ['article', 'main', '[role="main"]', '.post-content', 'body']:
                element = await page.query_selector(selector)
                if element:
                    content = await element.inner_text()
                    if len(content.strip()) > 100:
                        break

            result.title = await page.title()
            result.content_length = len(content)
            result.success = result.content_length > 100

        except Exception as e:
            result.error = str(e)

        result.duration_ms = (time.time() - start_time) * 1000
        return result

    async def strategy_with_debugging(self, page: Page, url: str) -> EnhancedScrapingResult:
        """Strategy 6: Debug mode - capture screenshots and HTML"""
        start_time = time.time()
        result = EnhancedScrapingResult(url=url, success=False, strategy="debug_mode")

        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)

            # Save initial state
            await page.screenshot(path="/home/user/pyDigestor/poc/debug_initial.png")
            print("  📸 Saved screenshot: debug_initial.png")

            # Handle cookies
            try:
                await page.click('button:has-text("Accept")', timeout=2000)
                await page.wait_for_timeout(1000)
                await page.screenshot(path="/home/user/pyDigestor/poc/debug_after_cookie.png")
                print("  📸 Saved screenshot: debug_after_cookie.png")
            except:
                pass

            await page.wait_for_load_state("networkidle", timeout=30000)

            # Save final state
            await page.screenshot(path="/home/user/pyDigestor/poc/debug_final.png")
            print("  📸 Saved screenshot: debug_final.png")

            # Save HTML
            html_content = await page.content()
            with open("/home/user/pyDigestor/poc/debug_page.html", "w", encoding="utf-8") as f:
                f.write(html_content)
            print("  💾 Saved HTML: debug_page.html")
            result.html_saved = True

            # Get page info
            print(f"  📊 Page URL: {page.url}")
            print(f"  📊 Page title: {await page.title()}")

            # Check for content elements
            all_articles = await page.query_selector_all('article')
            all_mains = await page.query_selector_all('main')
            print(f"  📊 Found {len(all_articles)} <article> elements")
            print(f"  📊 Found {len(all_mains)} <main> elements")

            content = ""
            for selector in ['article', 'main', '[role="main"]', '.post-content', 'body']:
                element = await page.query_selector(selector)
                if element:
                    content = await element.inner_text()
                    print(f"  📊 Selector '{selector}' returned {len(content)} chars")
                    if len(content.strip()) > 100:
                        break

            result.title = await page.title()
            result.content_length = len(content)
            result.success = result.content_length > 100
            result.screenshot_path = "/home/user/pyDigestor/poc/debug_final.png"

        except Exception as e:
            result.error = str(e)

        result.duration_ms = (time.time() - start_time) * 1000
        return result

    async def run_enhanced_tests(self):
        """Run all enhanced scraping strategies"""
        async with async_playwright() as p:
            print("=" * 80)
            print("Enhanced Playwright Web Scraping POC")
            print("=" * 80)
            print(f"\nTarget: {self.TARGET_URL}")
            print("\nTesting various strategies to extract content...\n")

            browser = await p.chromium.launch(headless=True)

            strategies = [
                ("Basic (baseline)", self.strategy_basic),
                ("Cookie Consent", self.strategy_with_cookies),
                ("Scroll & Lazy Load", self.strategy_with_scroll),
                ("Wait for Selector", self.strategy_wait_for_selector),
                ("Longer Timeout", self.strategy_longer_timeout),
                ("Debug Mode", self.strategy_with_debugging),
            ]

            for strategy_name, strategy_func in strategies:
                print(f"\n{'='*80}")
                print(f"Strategy: {strategy_name}")
                print(f"{'='*80}")

                page = await browser.new_page()
                try:
                    result = await strategy_func(page, self.TARGET_URL)
                    self.results.append(result)
                    self.print_result(result)
                finally:
                    await page.close()

            await browser.close()

    def print_result(self, result: EnhancedScrapingResult):
        """Print result of a scraping strategy"""
        status = "✓ SUCCESS" if result.success else "✗ FAILED"
        print(f"\n  Status: {status}")
        print(f"  Duration: {result.duration_ms:.2f}ms")
        print(f"  Title: {result.title or 'N/A'}")
        print(f"  Content Length: {result.content_length} chars")

        if result.error:
            print(f"  Error: {result.error}")

        if result.screenshot_path:
            print(f"  Screenshot: {result.screenshot_path}")

        if result.html_saved:
            print(f"  HTML saved for inspection")

    def print_summary(self):
        """Print summary and recommendations"""
        print("\n" + "=" * 80)
        print("SUMMARY")
        print("=" * 80)
        print()

        total = len(self.results)
        successful = sum(1 for r in self.results if r.success)

        print(f"Total Strategies Tested: {total}")
        print(f"Successful: {successful}")
        print(f"Failed: {total - successful}")
        print()

        print("Results by Strategy:")
        print("-" * 80)
        for result in self.results:
            status = "✓" if result.success else "✗"
            print(f"{status} {result.strategy:20} | {result.content_length:6} chars | {result.duration_ms:8.1f}ms")

        print("\n" + "=" * 80)
        print("RECOMMENDATIONS")
        print("=" * 80)
        print()

        if successful:
            winning_strategies = [r for r in self.results if r.success]
            print("✓ Working strategies found:")
            for r in winning_strategies:
                print(f"  - {r.strategy}: {r.content_length} chars in {r.duration_ms:.1f}ms")

            print("\n💡 Use the fastest working strategy for production")
        else:
            print("⚠ No strategies worked. Additional investigation needed:")
            print("  1. Check debug_*.png screenshots to see what the page looks like")
            print("  2. Review debug_page.html to inspect the HTML structure")
            print("  3. Site may have:")
            print("     - Geographic restrictions (blocked region)")
            print("     - CAPTCHA challenges")
            print("     - Advanced bot detection (Cloudflare, Imperva, etc.)")
            print("     - Content behind authentication")
            print("     - JavaScript errors preventing content load")
            print("\n💡 Next steps:")
            print("  - Try with headed mode (headless=False) to see browser behavior")
            print("  - Use browser DevTools to inspect network requests")
            print("  - Check if site works in regular browser from same environment")
            print("  - Consider using residential proxies")
            print("  - Look for official API as alternative")


async def main():
    """Run the enhanced POC"""
    poc = EnhancedPlaywrightPOC()
    await poc.run_enhanced_tests()
    poc.print_summary()


if __name__ == "__main__":
    asyncio.run(main())
