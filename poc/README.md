# Playwright Web Scraping POC

This proof of concept tests the minimal requirements for web scraping using Playwright.

## Objective

Determine what configuration is needed to successfully scrape content from various websites, including:
- https://webdecoy.com/blog/ja4-fingerprinting-ai-scrapers-practical-guide/
- https://randywestergren.com/vibe-hacking-proxying-flutter-traffic-on-android-with-claude/
- https://www.group-ib.com/blog/ghost-tapped-chinese-malware/

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
# Run the POC script
uv run python poc/playwright_scraping_poc.py
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
