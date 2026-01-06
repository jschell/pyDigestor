"""Tests for content extraction."""

from unittest.mock import Mock, patch

import pytest
import httpx

from pydigestor.sources.extraction import ContentExtractor


class TestContentExtractor:
    """Tests for ContentExtractor class."""

    def test_init(self):
        """Test ContentExtractor initialization."""
        extractor = ContentExtractor()
        assert extractor.timeout == 10
        assert extractor.max_retries == 2
        assert len(extractor.failed_urls) == 0

    def test_init_custom_timeout(self):
        """Test ContentExtractor with custom timeout."""
        extractor = ContentExtractor(timeout=30, max_retries=5)
        assert extractor.timeout == 30
        assert extractor.max_retries == 5

    @patch("pydigestor.sources.extraction.httpx.get")
    @patch("pydigestor.sources.extraction.trafilatura.extract")
    def test_extract_with_trafilatura_success(self, mock_trafilatura, mock_get):
        """Test successful extraction with trafilatura."""
        # Mock HTTP response
        mock_response = Mock()
        mock_response.content = b"<html>Article content</html>"
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        # Mock trafilatura extraction
        mock_trafilatura.return_value = "This is a long article content that is definitely more than 100 characters to pass validation and ensure successful extraction."

        extractor = ContentExtractor()
        content = extractor.extract("https://example.com/article")

        assert content is not None
        assert len(content) > 100
        assert extractor.metrics["trafilatura_success"] == 1
        assert extractor.metrics["total_attempts"] == 1

    @patch("pydigestor.sources.extraction.httpx.get")
    @patch("pydigestor.sources.extraction.trafilatura.extract")
    @patch("pydigestor.sources.extraction.NewspaperArticle")
    def test_extract_with_newspaper_fallback(
        self, mock_newspaper_class, mock_trafilatura, mock_get
    ):
        """Test fallback to newspaper3k when trafilatura fails."""
        # Mock HTTP response
        mock_response = Mock()
        mock_response.content = b"<html>Article content</html>"
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        # Mock trafilatura to return short content (fails validation)
        mock_trafilatura.return_value = "Short"

        # Mock newspaper3k extraction
        mock_article = Mock()
        mock_article.text = "This is a long article content from newspaper3k that is definitely more than 100 characters to pass validation."
        mock_newspaper_class.return_value = mock_article

        extractor = ContentExtractor()
        content = extractor.extract("https://example.com/article")

        assert content is not None
        assert len(content) > 100
        assert extractor.metrics["trafilatura_success"] == 0
        assert extractor.metrics["newspaper_success"] == 1
        assert extractor.metrics["total_attempts"] == 1

    @patch("pydigestor.sources.extraction.httpx.get")
    def test_extract_http_timeout(self, mock_get):
        """Test handling of HTTP timeouts."""
        # Mock timeout error
        mock_get.side_effect = httpx.TimeoutException("Connection timeout")

        extractor = ContentExtractor()
        content = extractor.extract("https://example.com/article")

        assert content is None
        assert extractor.metrics["failures"] == 1
        assert "https://example.com/article" in extractor.failed_urls

    @patch("pydigestor.sources.extraction.httpx.get")
    def test_extract_http_error(self, mock_get):
        """Test handling of HTTP errors."""
        # Mock HTTP error
        mock_get.side_effect = httpx.HTTPError("404 Not Found")

        extractor = ContentExtractor()
        content = extractor.extract("https://example.com/article")

        assert content is None
        assert extractor.metrics["failures"] == 1

    def test_extract_cached_failure(self):
        """Test that failed URLs are cached and not retried."""
        extractor = ContentExtractor()
        extractor.failed_urls.add("https://example.com/bad-url")

        # Try to extract from cached failed URL
        content = extractor.extract("https://example.com/bad-url")

        assert content is None
        assert extractor.metrics["cached_failures"] == 1
        assert extractor.metrics["total_attempts"] == 0  # Not attempted

    @patch("pydigestor.sources.extraction.httpx.get")
    @patch("pydigestor.sources.extraction.trafilatura.extract")
    def test_extract_short_content_rejected(self, mock_trafilatura, mock_get):
        """Test that content shorter than 100 chars is rejected."""
        # Mock HTTP response
        mock_response = Mock()
        mock_response.content = b"<html>Short</html>"
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        # Mock trafilatura to return short content
        mock_trafilatura.return_value = "Short content"

        # Mock newspaper to also fail
        with patch("pydigestor.sources.extraction.NewspaperArticle") as mock_newspaper:
            mock_article = Mock()
            mock_article.text = "Also short"
            mock_newspaper.return_value = mock_article

            extractor = ContentExtractor()
            content = extractor.extract("https://example.com/article")

            assert content is None
            assert extractor.metrics["failures"] == 1

    def test_get_metrics(self):
        """Test metrics retrieval."""
        extractor = ContentExtractor()

        # Initial metrics
        metrics = extractor.get_metrics()
        assert metrics["success_rate"] == 0
        assert metrics["total_attempts"] == 0

        # Simulate some successful extractions
        extractor.metrics["total_attempts"] = 10
        extractor.metrics["trafilatura_success"] = 7
        extractor.metrics["newspaper_success"] = 2
        extractor.metrics["failures"] = 1

        metrics = extractor.get_metrics()
        assert metrics["success_rate"] == 90.0  # 9/10 = 90%
        assert metrics["total_attempts"] == 10
        assert metrics["trafilatura_success"] == 7
        assert metrics["newspaper_success"] == 2

    def test_reset_metrics(self):
        """Test resetting metrics."""
        extractor = ContentExtractor()

        # Set some metrics
        extractor.metrics["total_attempts"] = 10
        extractor.metrics["trafilatura_success"] = 5

        # Reset
        extractor.reset_metrics()

        assert extractor.metrics["total_attempts"] == 0
        assert extractor.metrics["trafilatura_success"] == 0

    @patch("pydigestor.sources.extraction.NewspaperArticle")
    @patch("pydigestor.sources.extraction.httpx.get")
    @patch("pydigestor.sources.extraction.trafilatura.extract")
    def test_multiple_extractions(self, mock_trafilatura, mock_get, mock_newspaper):
        """Test multiple extractions update metrics correctly."""
        # Mock HTTP response
        mock_response = Mock()
        mock_response.content = b"<html>Content</html>"
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        # Mock trafilatura to succeed
        mock_trafilatura.return_value = "This is a long article content that is definitely more than 100 characters to pass validation."

        # Mock newspaper3k (shouldn't be called, but prevent real HTTP)
        mock_article = Mock()
        mock_article.text = "Fallback content"
        mock_newspaper.return_value = mock_article

        extractor = ContentExtractor()

        # Extract from multiple URLs
        extractor.extract("https://example.com/article1")
        extractor.extract("https://example.com/article2")
        extractor.extract("https://example.com/article3")

        assert extractor.metrics["total_attempts"] == 3
        assert extractor.metrics["trafilatura_success"] == 3
        assert extractor.metrics["failures"] == 0

    @patch("pydigestor.sources.extraction.httpx.get")
    @patch("pydigestor.sources.extraction.trafilatura.extract")
    def test_extract_with_none_content(self, mock_trafilatura, mock_get):
        """Test handling of None content from trafilatura."""
        # Mock HTTP response
        mock_response = Mock()
        mock_response.content = b"<html>Content</html>"
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        # Mock trafilatura to return None
        mock_trafilatura.return_value = None

        # Mock newspaper to also fail
        with patch("pydigestor.sources.extraction.NewspaperArticle") as mock_newspaper:
            mock_article = Mock()
            mock_article.text = None
            mock_newspaper.return_value = mock_article

            extractor = ContentExtractor()
            content = extractor.extract("https://example.com/article")

            assert content is None
            assert extractor.metrics["failures"] == 1
