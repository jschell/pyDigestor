"""Playwright plugin for pyDigestor.

This plugin enables extraction from JavaScript-heavy websites that require
browser automation. It uses Playwright to render pages and extract content
after JavaScript execution.

Installation:
    pip install pydigestor-playwright

Usage:
    The plugin registers automatically when installed. No configuration needed.
    pyDigestor will use Playwright for sites that require it.

Supported Sites:
    - Sites behind cookie consent banners
    - JavaScript-rendered content
    - Dynamic loading with infinite scroll
    - Sites requiring user agent spoofing
"""

import pluggy

from .extractor import PlaywrightExtractor

__version__ = "0.1.0"

hookimpl = pluggy.HookimplMarker("pydigestor")


@hookimpl
def register_extractors(registry):
    """
    Register Playwright-based extraction patterns.

    This hook is called by pyDigestor during initialization to register
    extraction patterns that use Playwright for content extraction.

    Args:
        registry: PatternRegistry instance to register patterns with
    """
    from pydigestor.sources.extraction import ExtractionPattern

    # Create extractor instance
    extractor = PlaywrightExtractor()

    # Register patterns for sites that commonly need Playwright
    # Priority 7: Higher than generic extractors, lower than PDFs

    # Wall Street Journal - often behind paywall/cookie consent
    registry.register(
        ExtractionPattern(
            name="playwright_wsj",
            domains=["wsj.com"],
            handler=extractor.extract,
            priority=7,
        )
    )

    # Twitter/X - requires JavaScript
    registry.register(
        ExtractionPattern(
            name="playwright_twitter",
            domains=["twitter.com", "x.com"],
            handler=extractor.extract,
            priority=7,
        )
    )

    # Medium - often behind login walls
    registry.register(
        ExtractionPattern(
            name="playwright_medium",
            domains=["medium.com"],
            handler=extractor.extract,
            priority=7,
        )
    )

    # Generic fallback for other JS-heavy sites (lower priority)
    # This can be triggered via config overrides
    registry.register(
        ExtractionPattern(
            name="playwright",
            domains=[],  # No auto-match, must be explicitly configured
            handler=extractor.extract,
            priority=1,
        )
    )
