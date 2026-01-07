"""Tests for content extraction."""

import io
from unittest.mock import Mock, patch, MagicMock

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
        mock_response.text = "<html>Article content</html>"
        mock_response.url = "https://example.com/article"  # Mock final URL
        mock_get.return_value = mock_response

        # Mock trafilatura extraction
        mock_trafilatura.return_value = "This is a long article content that is definitely more than 100 characters to pass validation and ensure successful extraction."

        extractor = ContentExtractor()
        content, resolved_url = extractor.extract("https://example.com/article")

        assert content is not None
        assert len(content) > 100
        assert resolved_url == "https://example.com/article"
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
        mock_response.text = "<html>Article content</html>"
        mock_response.url = "https://example.com/article"  # Mock final URL
        mock_get.return_value = mock_response

        # Mock trafilatura to return short content (fails validation)
        mock_trafilatura.return_value = "Short"

        # Mock newspaper3k extraction
        mock_article = Mock()
        mock_article.text = "This is a long article content from newspaper3k that is definitely more than 100 characters to pass validation."
        mock_article.url = "https://example.com/article"  # Mock article URL
        mock_newspaper_class.return_value = mock_article

        extractor = ContentExtractor()
        content, resolved_url = extractor.extract("https://example.com/article")

        assert content is not None
        assert len(content) > 100
        assert resolved_url == "https://example.com/article"
        assert extractor.metrics["trafilatura_success"] == 0
        assert extractor.metrics["newspaper_success"] == 1
        assert extractor.metrics["total_attempts"] == 1

    @patch("pydigestor.sources.extraction.httpx.get")
    def test_extract_http_timeout(self, mock_get):
        """Test handling of HTTP timeouts."""
        # Mock timeout error
        mock_get.side_effect = httpx.TimeoutException("Connection timeout")

        extractor = ContentExtractor()
        content, resolved_url = extractor.extract("https://example.com/article")

        assert content is None
        assert resolved_url == "https://example.com/article"
        assert extractor.metrics["failures"] == 1
        assert "https://example.com/article" in extractor.failed_urls

    @patch("pydigestor.sources.extraction.httpx.get")
    def test_extract_http_error(self, mock_get):
        """Test handling of HTTP errors."""
        # Mock HTTP error
        mock_get.side_effect = httpx.HTTPError("404 Not Found")

        extractor = ContentExtractor()
        content, resolved_url = extractor.extract("https://example.com/article")

        assert content is None
        assert resolved_url == "https://example.com/article"
        assert extractor.metrics["failures"] == 1

    def test_extract_cached_failure(self):
        """Test that failed URLs are cached and not retried."""
        extractor = ContentExtractor()
        extractor.failed_urls.add("https://example.com/bad-url")

        # Try to extract from cached failed URL
        content, resolved_url = extractor.extract("https://example.com/bad-url")

        assert content is None
        assert resolved_url == "https://example.com/bad-url"
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
            content, resolved_url = extractor.extract("https://example.com/article")

            assert content is None
            assert resolved_url == "https://example.com/article"
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
        mock_response.text = "<html>Content</html>"
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        # Mock trafilatura to succeed - must return content > 100 chars (exactly 101 chars for clarity)
        expected_content = "This is a long article content that is definitely more than one hundred characters long to pass validation successfully!"
        mock_trafilatura.return_value = expected_content

        # Mock newspaper3k (shouldn't be called, but prevent real HTTP)
        mock_article = Mock()
        mock_article.text = "Fallback content that is also more than 100 characters to pass validation checks."
        mock_newspaper.return_value = mock_article

        extractor = ContentExtractor()

        # Extract from multiple URLs (non-Medium to avoid BeautifulSoup complexity)
        _, _ = extractor.extract("https://example.com/article1")
        _, _ = extractor.extract("https://example.com/article2")
        _, _ = extractor.extract("https://example.com/article3")

        # All extractions should succeed
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
            content, resolved_url = extractor.extract("https://example.com/article")

            assert content is None
            assert resolved_url == "https://example.com/article"
            assert extractor.metrics["failures"] == 1

    # PDF Extraction Tests

    def test_is_pdf_url_with_pdf_extension(self):
        """Test PDF URL detection with .pdf extension."""
        extractor = ContentExtractor()
        assert extractor._is_pdf_url("https://example.com/paper.pdf") is True
        assert extractor._is_pdf_url("https://arxiv.org/pdf/2501.12345.pdf") is True

    def test_is_pdf_url_with_pdf_path(self):
        """Test PDF URL detection with /pdf/ in path."""
        extractor = ContentExtractor()
        assert extractor._is_pdf_url("https://arxiv.org/pdf/2501.12345") is True
        assert extractor._is_pdf_url("https://example.com/PDF/document") is True  # Case insensitive

    def test_is_pdf_url_non_pdf(self):
        """Test PDF URL detection returns False for non-PDF URLs."""
        extractor = ContentExtractor()
        assert extractor._is_pdf_url("https://example.com/article") is False
        assert extractor._is_pdf_url("https://arxiv.org/abs/2501.12345") is False

    def test_convert_arxiv_to_pdf_abstract_url(self):
        """Test conversion of arXiv abstract URL to PDF URL."""
        extractor = ContentExtractor()

        original = "https://arxiv.org/abs/2501.12345"
        expected = "https://arxiv.org/pdf/2501.12345.pdf"

        result = extractor._convert_arxiv_to_pdf(original)
        assert result == expected

    def test_convert_arxiv_to_pdf_http(self):
        """Test conversion works with http (not just https)."""
        extractor = ContentExtractor()

        original = "http://arxiv.org/abs/2501.12345"
        expected = "https://arxiv.org/pdf/2501.12345.pdf"

        result = extractor._convert_arxiv_to_pdf(original)
        assert result == expected

    def test_convert_arxiv_to_pdf_non_arxiv_url(self):
        """Test that non-arXiv URLs are returned unchanged."""
        extractor = ContentExtractor()

        url = "https://example.com/paper.pdf"
        result = extractor._convert_arxiv_to_pdf(url)
        assert result == url

    def test_convert_arxiv_to_pdf_already_pdf(self):
        """Test that arXiv PDF URLs are returned unchanged."""
        extractor = ContentExtractor()

        url = "https://arxiv.org/pdf/2501.12345.pdf"
        result = extractor._convert_arxiv_to_pdf(url)
        assert result == url

    @patch("pydigestor.sources.extraction.pdfplumber.open")
    @patch("pydigestor.sources.extraction.httpx.get")
    def test_extract_pdf_success(self, mock_get, mock_pdfplumber):
        """Test successful PDF extraction."""
        # Mock HTTP response with PDF
        mock_response = Mock()
        mock_response.content = b"PDF binary content"
        mock_response.headers = {"content-type": "application/pdf"}
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        # Mock pdfplumber PDF extraction
        mock_pdf = MagicMock()
        mock_page1 = Mock()
        mock_page1.extract_text.return_value = "First page content with enough text to pass validation. " * 10
        mock_page2 = Mock()
        mock_page2.extract_text.return_value = "Second page content with more text. " * 10

        mock_pdf.pages = [mock_page1, mock_page2]
        mock_pdf.__enter__.return_value = mock_pdf
        mock_pdf.__exit__.return_value = False
        mock_pdfplumber.return_value = mock_pdf

        extractor = ContentExtractor()
        content = extractor._extract_pdf("https://example.com/paper.pdf")

        assert content is not None
        assert len(content) > 500
        assert "First page" in content
        assert "Second page" in content

    @patch("pydigestor.sources.extraction.httpx.get")
    def test_extract_pdf_http_error(self, mock_get):
        """Test handling of HTTP errors during PDF download."""
        mock_get.side_effect = httpx.HTTPError("404 Not Found")

        extractor = ContentExtractor()
        content = extractor._extract_pdf("https://example.com/paper.pdf")

        assert content is None

    @patch("pydigestor.sources.extraction.httpx.get")
    def test_extract_pdf_timeout(self, mock_get):
        """Test handling of timeout during PDF download."""
        mock_get.side_effect = httpx.TimeoutException("Download timeout")

        extractor = ContentExtractor()
        content = extractor._extract_pdf("https://example.com/paper.pdf")

        assert content is None

    @patch("pydigestor.sources.extraction.httpx.get")
    def test_extract_pdf_wrong_content_type(self, mock_get):
        """Test rejection of non-PDF content type."""
        mock_response = Mock()
        mock_response.content = b"HTML content"
        mock_response.headers = {"content-type": "text/html"}
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        extractor = ContentExtractor()
        content = extractor._extract_pdf("https://example.com/not-a-pdf")

        assert content is None

    @patch("pydigestor.sources.extraction.pdfplumber.open")
    @patch("pydigestor.sources.extraction.httpx.get")
    def test_extract_pdf_minimal_text(self, mock_get, mock_pdfplumber):
        """Test rejection of PDFs with minimal text."""
        mock_response = Mock()
        mock_response.content = b"PDF binary"
        mock_response.headers = {"content-type": "application/pdf"}
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        # Mock PDF with very little text
        mock_pdf = MagicMock()
        mock_page = Mock()
        mock_page.extract_text.return_value = "Short"
        mock_pdf.pages = [mock_page]
        mock_pdf.__enter__.return_value = mock_pdf
        mock_pdf.__exit__.return_value = False
        mock_pdfplumber.return_value = mock_pdf

        extractor = ContentExtractor()
        content = extractor._extract_pdf("https://example.com/paper.pdf")

        assert content is None

    @patch("pydigestor.sources.extraction.pdfplumber.open")
    @patch("pydigestor.sources.extraction.httpx.get")
    def test_extract_arxiv_pdf_integration(self, mock_get, mock_pdfplumber):
        """Test full integration: arXiv abstract URL -> PDF extraction."""
        # Mock HTTP response
        mock_response = Mock()
        mock_response.content = b"PDF content"
        mock_response.headers = {"content-type": "application/pdf"}
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        # Mock pdfplumber
        mock_pdf = MagicMock()
        mock_page = Mock()
        mock_page.extract_text.return_value = "Academic paper content with sufficient text to pass validation. " * 50
        mock_pdf.pages = [mock_page]
        mock_pdf.__enter__.return_value = mock_pdf
        mock_pdf.__exit__.return_value = False
        mock_pdfplumber.return_value = mock_pdf

        extractor = ContentExtractor()
        # Start with arXiv abstract URL
        content, final_url = extractor.extract("https://arxiv.org/abs/2501.12345")

        # Should convert to PDF URL and extract content
        assert content is not None
        assert len(content) > 500
        assert "Academic paper" in content
        assert final_url == "https://arxiv.org/pdf/2501.12345.pdf"
        assert extractor.metrics["trafilatura_success"] == 1
