"""
HTTP-only Web Scraping Comparison POC

Tests what can be achieved with simple HTTP requests vs JavaScript-enabled browsing.
This helps determine when Playwright is truly needed vs when httpx/trafilatura is sufficient.
"""

import asyncio
import time
from typing import Optional
from dataclasses import dataclass

import httpx
from trafilatura import extract
from bs4 import BeautifulSoup


@dataclass
class HttpScrapingResult:
    """Result of an HTTP-based scraping attempt"""
    url: str
    success: bool
    content_length: int = 0
    title: Optional[str] = None
    error: Optional[str] = None
    duration_ms: float = 0
    method: str = ""
    main_content_preview: str = ""
    http_status: int = 0


class HttpScrapingPOC:
    """POC for testing HTTP-only scraping capabilities"""

    TARGET_URLS = [
        "https://webdecoy.com/blog/ja4-fingerprinting-ai-scrapers-practical-guide/",
        "https://randywestergren.com/vibe-hacking-proxying-flutter-traffic-on-android-with-claude/",
        "https://www.group-ib.com/blog/ghost-tapped-chinese-malware/",
    ]

    def __init__(self):
        self.results: list[HttpScrapingResult] = []

    async def scrape_with_httpx_basic(self, url: str) -> HttpScrapingResult:
        """Scrape with basic httpx GET request"""
        start_time = time.time()
        result = HttpScrapingResult(url=url, success=False, method="httpx_basic")

        try:
            async with httpx.AsyncClient(
                follow_redirects=True,
                timeout=30.0
            ) as client:
                response = await client.get(url)
                result.http_status = response.status_code

                if response.status_code == 200:
                    html = response.text
                    soup = BeautifulSoup(html, 'html.parser')

                    # Get title
                    title_tag = soup.find('title')
                    result.title = title_tag.get_text() if title_tag else None

                    # Try to find main content
                    content = ""
                    for selector in ['article', 'main', '[role="main"]', 'body']:
                        element = soup.select_one(selector)
                        if element:
                            content = element.get_text(separator='\n', strip=True)
                            if len(content) > 100:
                                break

                    result.content_length = len(content)
                    result.main_content_preview = content[:500] if content else ""
                    result.success = result.content_length > 100
                else:
                    result.error = f"HTTP {response.status_code}"

        except Exception as e:
            result.error = str(e)

        result.duration_ms = (time.time() - start_time) * 1000
        return result

    async def scrape_with_httpx_headers(self, url: str) -> HttpScrapingResult:
        """Scrape with custom headers to mimic a real browser"""
        start_time = time.time()
        result = HttpScrapingResult(url=url, success=False, method="httpx_with_headers")

        headers = {
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }

        try:
            async with httpx.AsyncClient(
                follow_redirects=True,
                timeout=30.0,
                headers=headers
            ) as client:
                response = await client.get(url)
                result.http_status = response.status_code

                if response.status_code == 200:
                    html = response.text
                    soup = BeautifulSoup(html, 'html.parser')

                    title_tag = soup.find('title')
                    result.title = title_tag.get_text() if title_tag else None

                    content = ""
                    for selector in ['article', 'main', '[role="main"]', 'body']:
                        element = soup.select_one(selector)
                        if element:
                            content = element.get_text(separator='\n', strip=True)
                            if len(content) > 100:
                                break

                    result.content_length = len(content)
                    result.main_content_preview = content[:500] if content else ""
                    result.success = result.content_length > 100
                else:
                    result.error = f"HTTP {response.status_code}"

        except Exception as e:
            result.error = str(e)

        result.duration_ms = (time.time() - start_time) * 1000
        return result

    async def scrape_with_trafilatura(self, url: str) -> HttpScrapingResult:
        """Scrape with trafilatura for content extraction"""
        start_time = time.time()
        result = HttpScrapingResult(url=url, success=False, method="trafilatura")

        headers = {
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        }

        try:
            async with httpx.AsyncClient(
                follow_redirects=True,
                timeout=30.0,
                headers=headers
            ) as client:
                response = await client.get(url)
                result.http_status = response.status_code

                if response.status_code == 200:
                    html = response.text

                    # Use trafilatura for content extraction
                    content = extract(
                        html,
                        include_comments=False,
                        include_tables=True,
                        include_images=False,
                        output_format='txt'
                    )

                    if content:
                        result.content_length = len(content)
                        result.main_content_preview = content[:500]
                        result.success = True

                        # Get title from HTML
                        soup = BeautifulSoup(html, 'html.parser')
                        title_tag = soup.find('title')
                        result.title = title_tag.get_text() if title_tag else None
                    else:
                        result.error = "Trafilatura could not extract content"
                else:
                    result.error = f"HTTP {response.status_code}"

        except Exception as e:
            result.error = str(e)

        result.duration_ms = (time.time() - start_time) * 1000
        return result

    async def test_url(self, url: str):
        """Test a URL with all methods"""
        print(f"\n{'='*80}")
        print(f"Testing: {url}")
        print(f"{'='*80}\n")

        methods = [
            ("Basic httpx", self.scrape_with_httpx_basic),
            ("httpx with headers", self.scrape_with_httpx_headers),
            ("Trafilatura", self.scrape_with_trafilatura),
        ]

        for method_name, method_func in methods:
            print(f"\n{method_name}:")
            result = await method_func(url)
            self.results.append(result)
            self.print_result(result)

    def print_result(self, result: HttpScrapingResult):
        """Print a scraping result"""
        status = "✓ SUCCESS" if result.success else "✗ FAILED"
        print(f"  Status: {status}")
        print(f"  HTTP Status: {result.http_status}")
        print(f"  Title: {result.title or 'N/A'}")
        print(f"  Content Length: {result.content_length} chars")
        print(f"  Duration: {result.duration_ms:.2f}ms")

        if result.error:
            print(f"  Error: {result.error}")

        if result.main_content_preview:
            preview = result.main_content_preview.replace('\n', ' ')[:150]
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
            successful_methods = [r.method for r in url_results if r.success]
            print(f"\n{url}")
            print(f"  Success rate: {len(successful_methods)}/{len(url_results)}")
            if successful_methods:
                print(f"  Working methods: {', '.join(successful_methods)}")
            else:
                print(f"  No working methods found")
                for r in url_results:
                    if r.error:
                        print(f"    - {r.method}: {r.error[:100]}")

        print("\n" + "=" * 80)
        print("CONCLUSIONS")
        print("=" * 80)
        print()

        if successful:
            http_only_urls = []
            needs_js_urls = []

            for url in self.TARGET_URLS:
                url_results = [r for r in self.results if r.url == url]
                if any(r.success for r in url_results):
                    http_only_urls.append(url)
                else:
                    needs_js_urls.append(url)

            if http_only_urls:
                print("✓ Sites that work with HTTP-only scraping:")
                for url in http_only_urls:
                    print(f"  - {url}")
                print()

            if needs_js_urls:
                print("⚠ Sites that may need JavaScript rendering (Playwright):")
                for url in needs_js_urls:
                    print(f"  - {url}")
                print()

            print("RECOMMENDATIONS:")
            if all(any(r.success and 'trafilatura' in r.method for r in self.results if r.url == url) for url in self.TARGET_URLS):
                print("  ✓ Use trafilatura for all URLs - no Playwright needed")
            elif http_only_urls:
                print(f"  ✓ Use trafilatura for {len(http_only_urls)}/{len(self.TARGET_URLS)} URLs")
                if needs_js_urls:
                    print(f"  ⚠ Use Playwright for {len(needs_js_urls)} URLs that failed")
            else:
                print("  ⚠ All URLs failed with HTTP-only methods")
                print("  → Playwright with JavaScript rendering is required")
                print("  → May also need:")
                print("     - Stealth plugins to avoid bot detection")
                print("     - Cookie/consent banner automation")
                print("     - Longer wait times for dynamic content")
        else:
            print("⚠ All HTTP-only attempts failed")
            print()
            print("This indicates that Playwright is needed because:")
            print("  - Sites may require JavaScript for content rendering")
            print("  - Sites may have bot detection/protection")
            print("  - Sites may require cookie consent interaction")


async def main():
    """Run the POC"""
    poc = HttpScrapingPOC()

    print("=" * 80)
    print("HTTP-only Web Scraping Comparison POC")
    print("=" * 80)
    print()
    print("This POC tests whether simple HTTP requests are sufficient")
    print("or if JavaScript rendering (Playwright) is required.")
    print()

    for url in poc.TARGET_URLS:
        await poc.test_url(url)

    poc.print_summary()


if __name__ == "__main__":
    asyncio.run(main())
