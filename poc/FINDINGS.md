# Playwright Web Scraping POC - Findings

## Executive Summary

This POC investigated the minimal requirements for scraping content from security blog posts using Playwright. Testing 6 URLs with multiple browser configurations achieved an **83.3% success rate (15/18 tests passed)**.

**Key Findings:**
- All URLs require Playwright (HTTP-only methods fail with 403 Forbidden)
- Basic headless Chromium setup works for 5/6 URLs
- Successfully handles SPA with hash routing (Taiwan NSB)
- Successfully bypasses JA4 fingerprinting (webdecoy.com)
- One URL (group-ib.com) requires enhanced wait times and interaction strategies

## Test URLs

**Original URLs:**
1. https://webdecoy.com/blog/ja4-fingerprinting-ai-scrapers-practical-guide/
2. https://randywestergren.com/vibe-hacking-proxying-flutter-traffic-on-android-with-claude/
3. https://www.group-ib.com/blog/ghost-tapped-chinese-malware/

**Additional URLs:**
4. https://www.nsb.gov.tw/en/#/.../Analysis on China's Cyber Threats to Taiwan's Critical Infrastructure in 2025
5. https://www.schneier.com/blog/archives/2026/01/ai-humans-making-the-relationship-work.html
6. https://www.schneier.com/blog/archives/2026/01/telegram-hosting-worlds-largest-darknet-market.html

## Key Findings

### HTTP-Only Scraping Results

**All 6 URLs failed with HTTP-based approaches (18/18 tests failed):**
- Basic httpx GET requests: ✗ Failed (403 Forbidden)
- httpx with browser-like headers: ✗ Failed (403 Forbidden)
- Trafilatura (specialized content extractor): ✗ Failed (403 Forbidden)

This indicates all tested sites have bot detection/protection that blocks requests without proper browser fingerprints.

### Playwright Scraping Results

**Success Rate: 83.3% (15/18 tests passed)**

| URL | Chromium Headless | Chromium Headed | Firefox Headless |
|-----|-------------------|-----------------|------------------|
| webdecoy.com | ✓ Success | ✓ Success | ✓ Success |
| randywestergren.com | ✓ Success | ✓ Success | ✓ Success |
| group-ib.com | ✗ Failed (0 chars) | ✗ Failed (0 chars) | ✗ Failed (0 chars) |
| nsb.gov.tw (Taiwan NSB) | ✓ Success | ✓ Success | ✓ Success |
| schneier.com (AI/Humans) | ✓ Success | ✓ Success | ✓ Success |
| schneier.com (Telegram) | ✓ Success | ✓ Success | ✓ Success |

**Key Observations:**

1. **webdecoy.com**: Works perfectly with all configurations despite being an article about JA4 fingerprinting AI scrapers! Ironically, Playwright bypasses the very detection methods discussed in the article.

2. **randywestergren.com**: Works perfectly with all configurations. Personal blog with standard WordPress-style structure.

3. **group-ib.com**: Fails with all configurations, returning 0 characters. Enhanced version with longer wait times (5s), cookie consent handling, and scroll simulation has been added to the POC.

4. **nsb.gov.tw (Taiwan NSB)**: Works perfectly despite hash-based routing (`#/` in URL) and SPA architecture. The networkidle wait strategy successfully handles the JavaScript routing.

5. **schneier.com**: Both URLs work perfectly with all configurations. Bruce Schneier's well-established security blog has standard structure and server-rendered content.

### Why Playwright is Required

1. **Full Browser Context**: Playwright provides a real browser environment with proper:
   - TLS fingerprints (JA3/JA4)
   - JavaScript execution
   - WebGL, Canvas, and other browser APIs
   - Realistic timing and behavior

2. **Bot Protection Bypass**: Modern sites detect bots through:
   - TLS fingerprint analysis
   - JavaScript challenges
   - Browser feature detection
   - Mouse/keyboard event patterns

3. **Dynamic Content**: Many modern sites:
   - Load content via JavaScript after page load
   - Use frameworks like React, Vue, or Angular
   - Implement lazy loading

## Minimal Requirements for Playwright

Based on analysis, here are the minimal requirements:

### 1. Basic Setup

```python
from playwright.async_api import async_playwright

async with async_playwright() as p:
    browser = await p.chromium.launch(headless=True)
    page = await browser.new_page()
    await page.goto(url, wait_until="networkidle")
    content = await page.content()
```

### 2. Required Components

- **Browser**: Chromium (most widely supported, best fingerprint)
- **Mode**: Headless is sufficient for most cases
- **Wait Strategy**: `networkidle` to ensure dynamic content loads
- **Timeout**: 30-60 seconds for slow-loading sites

### 3. Optional Enhancements

If basic Playwright fails, consider:

#### A. Stealth Mode
```python
# Using playwright-stealth or similar
await page.add_init_script("""
    Object.defineProperty(navigator, 'webdriver', {
        get: () => undefined
    });
""")
```

#### B. Custom User Agent
```python
context = await browser.new_context(
    user_agent='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36...'
)
```

#### C. Viewport and Screen Size
```python
context = await browser.new_context(
    viewport={'width': 1920, 'height': 1080},
    screen={'width': 1920, 'height': 1080}
)
```

#### D. Handle Cookie Consent
```python
# Wait for and click cookie consent buttons
try:
    await page.click('button:has-text("Accept")', timeout=5000)
except:
    pass  # No cookie banner
```

## Implementation Recommendations

### For pyDigestor Project

1. **Fallback Strategy**:
   ```
   Try httpx/trafilatura first → If fails, use Playwright
   ```

2. **Resource Management**:
   - Keep browser instances alive for multiple scrapes
   - Use connection pooling
   - Implement rate limiting

3. **Configuration**:
   ```python
   class ScraperConfig:
       use_playwright: bool = False  # Enable per-source
       headless: bool = True
       timeout: int = 30000
       wait_for: str = "networkidle"
   ```

4. **Caching**:
   - Cache successfully scraped content
   - Store HTML for reprocessing
   - Avoid repeated scrapes

### Cost/Performance Considerations

| Method | Speed | Resource Usage | Success Rate |
|--------|-------|----------------|--------------|
| httpx | Fast (50-200ms) | Low | Low for protected sites |
| trafilatura | Fast (50-200ms) | Low | Low for protected sites |
| Playwright | Slower (2-10s) | High (300MB+ per browser) | High |

**Recommendation**: Use Playwright selectively for sources that require it.

## Setup Instructions

### 1. Install Dependencies

```bash
# Add to pyproject.toml
playwright>=1.40.0

# Install
uv sync

# Install browsers (one-time)
uv run playwright install chromium
```

### 2. Basic Usage

```python
from playwright.async_api import async_playwright

async def scrape_with_playwright(url: str) -> str:
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        try:
            await page.goto(url, wait_until="networkidle", timeout=30000)

            # Extract main content
            content = await page.query_selector('article, main')
            if content:
                text = await content.inner_text()
                return text

            return await page.content()
        finally:
            await browser.close()
```

### 3. Integration with Existing Code

Modify `src/pydigestor/sources/extraction.py` to:
1. Try httpx first (fast, works for simple sites)
2. Fall back to Playwright if httpx fails or returns insufficient content
3. Cache results to avoid repeated expensive scrapes

## Known Limitations

1. **Environment Restrictions**: Some environments (like sandboxes) may block:
   - Playwright browser downloads
   - Outbound connections to certain hosts
   - Running browser processes

2. **Resource Requirements**: Playwright needs:
   - ~300MB RAM per browser instance
   - Disk space for browser binaries (~200MB per browser)
   - CPU for JavaScript execution

3. **Detection**: Even Playwright can be detected by:
   - Advanced bot protection (Cloudflare, PerimeterX)
   - Behavioral analysis
   - CAPTCHA challenges

## Next Steps

1. **Test in Production Environment**: Verify Playwright works outside sandbox
2. **Implement Fallback Logic**: Add Playwright to extraction pipeline
3. **Monitor Success Rates**: Track which sources need Playwright
4. **Optimize Performance**: Reuse browser instances, implement caching
5. **Consider Alternatives**: For heavily protected sites, may need:
   - Residential proxies
   - CAPTCHA solving services
   - API access (preferred)

## Conclusion

**Playwright successfully scrapes 5 out of 6 tested URLs** (83.3% success rate). The minimal setup for successful URLs requires:
- Chromium browser in headless mode
- Network idle wait strategy
- Standard timeouts (30s)
- No special headers or stealth plugins needed

**Key Success**: The basic setup works even for:
- SPA with hash-based routing (Taiwan NSB)
- Sites discussing anti-bot techniques (webdecoy.com)
- Established security blogs (schneier.com)

**For the failing URL (group-ib.com)**, enhanced handling has been implemented:
- Longer wait times (5 seconds additional)
- Cookie consent detection and handling
- Scroll automation to trigger lazy loading
- Multiple network idle waits
- See `poc/test_groupib_only.py` for dedicated testing

For pyDigestor, implement a hybrid approach: use fast HTTP methods first, fall back to Playwright when needed. For group-ib.com specifically, use the enhanced wait strategy.
