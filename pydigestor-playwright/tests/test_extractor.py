"""Tests for PlaywrightExtractor class."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from pydigestor_playwright.extractor import PlaywrightExtractor


@pytest.mark.unit
class TestPlaywrightExtractorInit:
    """Test PlaywrightExtractor initialization."""

    def test_default_initialization(self):
        """Test default initialization parameters."""
        extractor = PlaywrightExtractor()
        assert extractor.headless is True
        assert extractor.timeout == 30000
        assert extractor._browser is None

    def test_custom_initialization(self):
        """Test custom initialization parameters."""
        extractor = PlaywrightExtractor(headless=False, timeout=60000)
        assert extractor.headless is False
        assert extractor.timeout == 60000


@pytest.mark.unit
class TestCookieConsentHandling:
    """Test cookie consent banner handling."""

    @pytest.mark.asyncio
    async def test_cookie_consent_found(self):
        """Test successful cookie consent button click."""
        extractor = PlaywrightExtractor()

        # Mock page
        mock_page = AsyncMock()
        mock_page.click = AsyncMock()
        mock_page.wait_for_timeout = AsyncMock()

        result = await extractor._handle_cookie_consent(mock_page)

        assert result is True
        assert mock_page.click.called

    @pytest.mark.asyncio
    async def test_cookie_consent_not_found(self):
        """Test when no cookie consent button exists."""
        extractor = PlaywrightExtractor()

        # Mock page that always times out
        mock_page = AsyncMock()
        from playwright.async_api import TimeoutError as PlaywrightTimeout

        mock_page.click = AsyncMock(side_effect=PlaywrightTimeout("Timeout"))

        result = await extractor._handle_cookie_consent(mock_page)

        assert result is False


@pytest.mark.unit
class TestContentExtraction:
    """Test content extraction logic."""

    @pytest.mark.asyncio
    async def test_extract_from_article_tag(self):
        """Test extraction from article tag."""
        extractor = PlaywrightExtractor()

        # Mock page and element
        mock_element = AsyncMock()
        mock_element.inner_text = AsyncMock(return_value="A" * 200)  # Valid content

        mock_page = AsyncMock()
        mock_page.query_selector = AsyncMock(return_value=mock_element)
        mock_page.title = AsyncMock(return_value="Test Article")

        content, title = await extractor._extract_content(mock_page)

        assert content is not None
        assert len(content) > 100
        assert title == "Test Article"

    @pytest.mark.asyncio
    async def test_extract_fallback_to_main(self):
        """Test fallback to main tag when article fails."""
        extractor = PlaywrightExtractor()

        # First selector returns None, second returns content
        mock_element = AsyncMock()
        mock_element.inner_text = AsyncMock(return_value="B" * 200)

        mock_page = AsyncMock()
        mock_page.query_selector = AsyncMock(side_effect=[None, mock_element])
        mock_page.title = AsyncMock(return_value="Test")

        content, title = await extractor._extract_content(mock_page)

        assert content is not None
        assert len(content) > 100

    @pytest.mark.asyncio
    async def test_extract_insufficient_content(self):
        """Test when extracted content is too short."""
        extractor = PlaywrightExtractor()

        mock_element = AsyncMock()
        mock_element.inner_text = AsyncMock(return_value="Short")  # Too short

        mock_page = AsyncMock()
        mock_page.query_selector = AsyncMock(return_value=mock_element)
        mock_page.title = AsyncMock(return_value="Test")

        content, title = await extractor._extract_content(mock_page)

        # Should continue trying other selectors
        assert mock_page.query_selector.call_count > 1


@pytest.mark.integration
class TestPlaywrightExtractorIntegration:
    """Integration tests requiring network access."""

    @pytest.mark.asyncio
    async def test_extract_simple_page(self):
        """Test extraction from a simple static page."""
        extractor = PlaywrightExtractor()

        # Use a simple, reliable test page
        url = "https://example.com"

        content, metadata = await extractor._extract_async(url)

        assert content is not None
        assert len(content) > 100
        assert metadata["extraction_method"] == "playwright"
        assert metadata["strategy"] in ["networkidle", "domcontentloaded"]
        assert metadata["error"] is None

        # Cleanup
        await extractor._close_browser()

    def test_extract_sync_wrapper(self):
        """Test synchronous extract wrapper."""
        extractor = PlaywrightExtractor()

        url = "https://example.com"
        content, metadata = extractor.extract(url)

        assert content is not None
        assert metadata["extraction_method"] == "playwright"


@pytest.mark.unit
class TestBrowserManagement:
    """Test browser lifecycle management."""

    @pytest.mark.asyncio
    async def test_browser_creation(self):
        """Test browser is created on first use."""
        extractor = PlaywrightExtractor()
        assert extractor._browser is None

        browser = await extractor._get_browser()
        assert browser is not None
        assert extractor._browser is not None

        await extractor._close_browser()

    @pytest.mark.asyncio
    async def test_browser_reuse(self):
        """Test browser is reused across calls."""
        extractor = PlaywrightExtractor()

        browser1 = await extractor._get_browser()
        browser2 = await extractor._get_browser()

        assert browser1 is browser2

        await extractor._close_browser()

    @pytest.mark.asyncio
    async def test_browser_close(self):
        """Test browser cleanup."""
        extractor = PlaywrightExtractor()

        await extractor._get_browser()
        assert extractor._browser is not None

        await extractor._close_browser()
        # After close, _browser should be None
        assert extractor._browser is None


@pytest.mark.unit
class TestErrorHandling:
    """Test error handling in various scenarios."""

    @pytest.mark.asyncio
    async def test_navigation_timeout(self):
        """Test handling of navigation timeouts."""
        extractor = PlaywrightExtractor(timeout=1)  # Very short timeout

        # Use a slow-loading or non-existent URL
        url = "https://httpstat.us/200?sleep=10000"

        content, metadata = await extractor._extract_async(url)

        # Should handle timeout gracefully
        assert metadata["error"] is not None
        assert content is None

        await extractor._close_browser()

    @pytest.mark.asyncio
    async def test_invalid_url(self):
        """Test handling of invalid URLs."""
        extractor = PlaywrightExtractor()

        url = "not-a-valid-url"

        content, metadata = await extractor._extract_async(url)

        assert content is None
        assert metadata["error"] is not None

        await extractor._close_browser()
