# Testing New URLs - Instructions

## New URLs Added

The following URLs have been added to both POC scripts for testing:

### 1. Taiwan NSB Cyber Threat Report
```
https://www.nsb.gov.tw/en/#/%E5%85%AC%E5%91%8A%E8%B3%87%E8%A8%8A/%E6%96%B0%E8%81%9E%E7%A8%BF%E6%9A%A8%E6%96%B0%E8%81%9E%E5%8F%83%E8%80%83%E8%B3%87%E6%96%99/2026-01-04/Analysis%20on%20China%E2%80%99s%20Cyber%20Threats%20to%20Taiwan%E2%80%99s%20Critical%20Infrastructure%20in%202025
```
**Characteristics:**
- Government website (Taiwan National Security Bureau)
- Hash-based routing (contains `#/`)
- URL-encoded Chinese characters in path
- Likely requires JavaScript for routing
- May require geographic considerations

### 2. Schneier on Security - AI & Humans Article
```
https://www.schneier.com/blog/archives/2026/01/ai-humans-making-the-relationship-work.html
```
**Characteristics:**
- Well-known security blog
- Static HTML structure (likely)
- Standard blog post format
- Expected to work well with Playwright

### 3. Schneier on Security - Telegram Article
```
https://www.schneier.com/blog/archives/2026/01/telegram-hosting-worlds-largest-darknet-market.html
```
**Characteristics:**
- Same domain as above
- Similar structure expected
- Standard blog post format

## Test Results

### HTTP-Only Testing (Already Completed)

All new URLs failed with **403 Forbidden** using HTTP-only methods:
- Basic httpx: ✗ Failed
- httpx with headers: ✗ Failed
- Trafilatura: ✗ Failed

This confirms Playwright is needed for these URLs.

## Running the Tests

### In Your Environment (where Playwright browsers are available)

```bash
# Run full Playwright POC on all 6 URLs
uv run python poc/playwright_scraping_poc.py

# Or run the HTTP comparison
uv run python poc/httpx_scraping_comparison.py
```

## Expected Results

### Taiwan NSB URL
**Prediction: May fail or return incomplete content**

Reasons:
1. **Hash-based routing** (`#/` in URL): Single-page application (SPA)
   - Content loaded via JavaScript after initial page load
   - May need to wait for JavaScript to parse the hash and load content
   - Playwright's `wait_until="networkidle"` should handle this

2. **URL-encoded path**: The path contains Chinese characters
   - Should be handled correctly by Playwright
   - May cause issues with some parsers

3. **Special considerations**:
   - Government website may have geographic restrictions
   - May require cookie consent
   - Content might be loaded asynchronously after hash routing

**Recommended approach if it fails**:
```python
# Wait longer for SPA to initialize
await page.goto(url, wait_until="domcontentloaded")
await page.wait_for_timeout(3000)  # Give SPA time to process hash
await page.wait_for_load_state("networkidle")
```

### Schneier URLs
**Prediction: Should work perfectly**

Reasons:
1. **Established blog**: Bruce Schneier's blog has been around for years
2. **Standard structure**: Likely uses WordPress or similar
3. **Static content**: Blog posts are typically server-rendered
4. **No heavy JavaScript**: Content should be available on initial load

**Expected success rate**: 100% (all browser configs)

## Analysis Questions

After running the tests, we want to know:

1. **Did the Taiwan NSB URL work?**
   - If no: Is it hash routing issue or geographic restriction?
   - Check the page title - does it show the article title?
   - Check content length - is it 0 or just low?

2. **Did Schneier URLs work?**
   - Expected to work perfectly
   - If they don't: Investigate why (unlikely)

3. **Browser compatibility**:
   - Do all browser configs work (Chromium/Firefox, headless/headed)?
   - Are there differences between browsers for these URLs?

4. **Performance comparison**:
   - How long does each URL take to scrape?
   - Taiwan NSB URL will likely be slower (SPA + international)
   - Schneier URLs should be fast

## Debugging the Taiwan NSB URL

If the Taiwan NSB URL fails or returns 0 chars, try the enhanced POC:

```bash
# Create a targeted test for just this URL
uv run python poc/playwright_enhanced_poc.py
```

You can modify the enhanced POC to target this specific URL and test:
1. Cookie consent handling
2. Longer wait times for SPA initialization
3. Explicit hash routing handling
4. Screenshot capture to see what's loading

## Example: Handling Hash-Based Routing

For SPAs with hash routing, you may need:

```python
await page.goto(url, wait_until="domcontentloaded")

# Wait for the app framework to initialize
await page.wait_for_timeout(2000)

# Wait for content to appear
await page.wait_for_selector('article, main, [class*="content"]', timeout=10000)

# Additional network idle wait
await page.wait_for_load_state("networkidle")
```

## Summary

**Total URLs now being tested: 6**
- Original 3: webdecoy.com, randywestergren.com, group-ib.com
- New 3: Taiwan NSB, Schneier (2 URLs)

**HTTP-only results: 0% success (all fail with 403)**

**Playwright results: TBD (please run and report)**

Expected outcome:
- Schneier URLs: High confidence they'll work (100% success)
- Taiwan NSB: Medium confidence (may need special handling for SPA)
- Overall success rate prediction: 55-77% (3-4 out of 6 new tests)
