# pyDigestor-Playwright

Playwright plugin for pyDigestor that enables content extraction from JavaScript-heavy websites requiring browser automation.

## Overview

This plugin extends pyDigestor with Playwright-based extraction capabilities, allowing you to scrape content from sites that:

- Require JavaScript rendering
- Hide content behind cookie consent banners
- Use dynamic content loading
- Employ anti-bot protection
- Need realistic browser interactions

## Installation

```bash
pip install pydigestor-playwright
```

After installation, you'll also need to install Playwright browsers:

```bash
playwright install chromium
```

## Usage

The plugin registers automatically when installed. No configuration needed.

```python
from pydigestor.sources.extraction import ContentExtractor

extractor = ContentExtractor()

# Automatically uses Playwright for supported sites
content, url = extractor.extract("https://www.wsj.com/articles/...")
```

## Supported Sites

The plugin automatically handles these sites:

- **Wall Street Journal** (`wsj.com`) - Paywalls and cookie consent
- **Twitter/X** (`twitter.com`, `x.com`) - JavaScript-rendered content
- **Medium** (`medium.com`) - Login walls and dynamic loading

For other JavaScript-heavy sites, you can configure pyDigestor to use Playwright via site-specific configuration.

## How It Works

The plugin uses multiple adaptive strategies:

1. **Network Idle Strategy**: Waits for network activity to settle
2. **Cookie Consent Handling**: Automatically clicks common consent buttons
3. **Dynamic Content Waiting**: Allows time for JavaScript to render
4. **Content Detection**: Waits for key content indicators before extraction
5. **Fallback Selectors**: Tries multiple content selectors (`article`, `main`, etc.)

## Architecture

### Plugin Registration

The plugin uses pyDigestor's pluggy-based plugin system:

```python
@hookimpl
def register_extractors(registry):
    """Register Playwright extraction patterns."""
    registry.register(ExtractionPattern(
        name="playwright_wsj",
        domains=["wsj.com"],
        handler=extractor.extract,
        priority=7
    ))
```

### Priority System

- **Priority 10**: File types (PDF)
- **Priority 7**: Site-specific Playwright patterns (WSJ, Twitter, Medium)
- **Priority 5**: Other site-specific extractors (GitHub)
- **Priority 1**: Generic Playwright (config-driven)
- **Default**: Trafilatura → Newspaper3k fallback

## Configuration

### Site-Specific Override

You can configure Playwright for any site using `~/.config/pydigestor/extractors.toml`:

```toml
[extraction.sites."example.com"]
method = "playwright"
timeout = 60
```

### Custom Timeout

```python
extractor = PlaywrightExtractor(timeout=60000)  # 60 seconds
```

### Headless Mode

```python
# Run with visible browser (for debugging)
extractor = PlaywrightExtractor(headless=False)
```

## Development

### Setup

```bash
cd pydigestor-playwright
pip install -e ".[dev]"
playwright install chromium
```

### Running Tests

```bash
# Unit tests only (fast, no network)
pytest -m unit

# Integration tests (requires network)
pytest -m integration

# All tests
pytest

# With coverage
pytest --cov=pydigestor_playwright --cov-report=html
```

### Test Structure

- `tests/test_extractor.py` - PlaywrightExtractor class tests
- `tests/test_plugin.py` - Plugin registration and integration tests

## Troubleshooting

### Browser Not Found

If you see "Executable doesn't exist" errors:

```bash
playwright install chromium
```

### Timeout Issues

Increase the timeout for slow sites:

```python
extractor = PlaywrightExtractor(timeout=90000)  # 90 seconds
```

### Cookie Consent Not Handled

The plugin tries common selectors. If a site uses unusual consent mechanisms, you may need to handle it manually or file an issue.

### Headless Detection

Some sites detect headless browsers. Try:

```python
extractor = PlaywrightExtractor(headless=False)
```

## Performance Considerations

Playwright extraction is slower than static extraction:

- **Static (trafilatura)**: ~500ms per URL
- **Playwright**: ~3-5 seconds per URL

Use Playwright only when necessary:
- Configure it for specific sites that need it
- Let pyDigestor's fallback system handle the rest

## Contributing

Contributions welcome! Areas for improvement:

- Additional site-specific handlers
- Better cookie consent detection
- Anti-bot evasion techniques
- Performance optimizations
- Mobile user agent strategies

## License

MIT License - see LICENSE file for details

## Credits

Built on top of:
- [Playwright](https://playwright.dev/) - Browser automation
- [pyDigestor](https://github.com/jschell/pyDigestor) - Feed aggregation and analysis
- [pluggy](https://pluggy.readthedocs.io/) - Plugin system

## Changelog

### 0.1.0 (2026-01-10)

- Initial release
- Support for WSJ, Twitter/X, Medium
- Cookie consent handling
- Dynamic content waiting
- Comprehensive test suite
