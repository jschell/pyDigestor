# Playwright Web Scraping POC

This proof of concept tests the minimal requirements for web scraping using Playwright.

## Objective

Determine what configuration is needed to successfully scrape content from various websites.

### Test URLs (6 total)

**Original URLs:**
- https://webdecoy.com/blog/ja4-fingerprinting-ai-scrapers-practical-guide/
- https://randywestergren.com/vibe-hacking-proxying-flutter-traffic-on-android-with-claude/
- https://www.group-ib.com/blog/ghost-tapped-chinese-malware/

**Additional URLs:**
- https://www.nsb.gov.tw/en/#/... (Taiwan NSB cyber threats report)
- https://www.schneier.com/blog/archives/2026/01/ai-humans-making-the-relationship-work.html
- https://www.schneier.com/blog/archives/2026/01/telegram-hosting-worlds-largest-darknet-market.html

## What It Tests

1. **Browser Types**: Chromium, Firefox, WebKit
2. **Headless vs Headed Mode**: Whether headless mode is sufficient
3. **Wait Strategies**: Testing different approaches to wait for content
4. **Content Extraction**: Finding the best selectors for blog content

## Setup

### Install Dependencies

```bash
# Install Python dependencies with uv
uv sync

# Install Playwright browsers
uv run playwright install
```

## Running the POC

```bash
# Run the full POC script (all 6 URLs, multiple browser configs)
uv run python poc/playwright_scraping_poc.py

# Run HTTP-only comparison to see which URLs need Playwright
uv run python poc/httpx_scraping_comparison.py

# Quick test: Just the 3 new URLs with basic config
uv run python poc/test_new_urls_only.py

# Enhanced debugging for difficult URLs
uv run python poc/playwright_enhanced_poc.py
```

## Output

The script will:
1. Test each URL with different browser configurations
2. Report success/failure for each attempt
3. Show content previews
4. Provide a summary with minimal requirements

## Expected Results

The POC will determine:
- Whether headless mode is sufficient
- Which browser engine works best
- What wait strategies are needed
- Whether special configuration (user agents, stealth plugins) is required

## Next Steps

Based on the POC results, integrate successful approaches into the main pyDigestor extraction pipeline.
