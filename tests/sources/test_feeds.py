"""Tests for RSS/Atom feed parsing."""

from datetime import datetime
from unittest.mock import Mock, patch
import time

import pytest
import httpx

from pydigestor.sources.feeds import FeedEntry, RSSFeedSource


class TestFeedEntry:
    """Tests for FeedEntry dataclass."""

    def test_feed_entry_creation(self):
        """Test creating a FeedEntry instance."""
        entry = FeedEntry(
            source_id="rss:example.com:abc123",
            url="https://example.com/article",
            title="Test Article",
            content="Article content",
            published_at=datetime(2024, 1, 1, 12, 0, 0),
        )

        assert entry.source_id == "rss:example.com:abc123"
        assert entry.url == "https://example.com/article"
        assert entry.title == "Test Article"
        assert entry.content == "Article content"
        assert entry.published_at == datetime(2024, 1, 1, 12, 0, 0)
        assert entry.tags == []  # Default empty list

    def test_feed_entry_with_tags(self):
        """Test FeedEntry with tags."""
        entry = FeedEntry(
            source_id="test",
            url="https://example.com",
            title="Test",
            tags=["security", "vulnerability"],
        )

        assert entry.tags == ["security", "vulnerability"]

    def test_generate_source_id(self):
        """Test source ID generation is consistent."""
        source_id1 = FeedEntry._generate_source_id(
            "https://example.com/feed",
            "https://example.com/article/123"
        )
        source_id2 = FeedEntry._generate_source_id(
            "https://example.com/feed",
            "https://example.com/article/123"
        )

        # Same inputs should generate same ID
        assert source_id1 == source_id2

        # ID should contain feed domain
        assert "example.com" in source_id1
        assert source_id1.startswith("rss:")

    def test_generate_source_id_different_urls(self):
        """Test source IDs are different for different URLs."""
        source_id1 = FeedEntry._generate_source_id(
            "https://example.com/feed",
            "https://example.com/article/123"
        )
        source_id2 = FeedEntry._generate_source_id(
            "https://example.com/feed",
            "https://example.com/article/456"
        )

        # Different article URLs should generate different IDs
        assert source_id1 != source_id2

    def test_from_feedparser_basic(self):
        """Test converting feedparser entry to FeedEntry."""
        feedparser_entry = {
            "link": "https://example.com/article",
            "title": "Test Article",
            "summary": "Test summary",
            "author": "John Doe",
        }

        entry = FeedEntry.from_feedparser(feedparser_entry, "https://example.com/feed")

        assert entry is not None
        assert entry.url == "https://example.com/article"
        assert entry.title == "Test Article"
        assert entry.summary == "Test summary"
        assert entry.author == "John Doe"

    def test_from_feedparser_missing_link(self):
        """Test that entries without links are rejected."""
        feedparser_entry = {
            "title": "Test Article",
            "summary": "Test summary",
        }

        entry = FeedEntry.from_feedparser(feedparser_entry, "https://example.com/feed")

        assert entry is None

    def test_from_feedparser_missing_title(self):
        """Test that entries without titles are rejected."""
        feedparser_entry = {
            "link": "https://example.com/article",
            "summary": "Test summary",
        }

        entry = FeedEntry.from_feedparser(feedparser_entry, "https://example.com/feed")

        assert entry is None

    def test_from_feedparser_with_content(self):
        """Test feedparser entry with content field."""
        feedparser_entry = {
            "link": "https://example.com/article",
            "title": "Test Article",
            "content": [{"value": "Full article content"}],
            "summary": "Short summary",
        }

        entry = FeedEntry.from_feedparser(feedparser_entry, "https://example.com/feed")

        assert entry.content == "Full article content"
        assert entry.summary == "Short summary"

    def test_from_feedparser_published_date(self):
        """Test parsing published date."""
        feedparser_entry = {
            "link": "https://example.com/article",
            "title": "Test Article",
            "published_parsed": time.struct_time((2024, 1, 15, 10, 30, 0, 0, 0, 0)),
        }

        entry = FeedEntry.from_feedparser(feedparser_entry, "https://example.com/feed")

        assert entry.published_at == datetime(2024, 1, 15, 10, 30, 0)

    def test_from_feedparser_updated_date_fallback(self):
        """Test falling back to updated date if no published date."""
        feedparser_entry = {
            "link": "https://example.com/article",
            "title": "Test Article",
            "updated_parsed": time.struct_time((2024, 1, 15, 10, 30, 0, 0, 0, 0)),
        }

        entry = FeedEntry.from_feedparser(feedparser_entry, "https://example.com/feed")

        assert entry.published_at == datetime(2024, 1, 15, 10, 30, 0)

    def test_from_feedparser_with_tags(self):
        """Test parsing tags from feedparser entry."""
        feedparser_entry = {
            "link": "https://example.com/article",
            "title": "Test Article",
            "tags": [
                {"term": "security"},
                {"term": "vulnerability"},
                {"term": ""},  # Empty tag should be filtered
            ],
        }

        entry = FeedEntry.from_feedparser(feedparser_entry, "https://example.com/feed")

        assert entry.tags == ["security", "vulnerability"]


class TestRSSFeedSource:
    """Tests for RSSFeedSource class."""

    def test_init(self):
        """Test RSSFeedSource initialization."""
        source = RSSFeedSource("https://example.com/feed")

        assert source.feed_url == "https://example.com/feed"
        assert source.timeout == 30

    def test_init_custom_timeout(self):
        """Test RSSFeedSource with custom timeout."""
        source = RSSFeedSource("https://example.com/feed", timeout=60)

        assert source.timeout == 60

    @patch("pydigestor.sources.feeds.httpx.get")
    @patch("pydigestor.sources.feeds.feedparser.parse")
    def test_fetch_success(self, mock_parse, mock_get):
        """Test successful feed fetch and parse."""
        # Mock HTTP response
        mock_response = Mock()
        mock_response.content = b"<rss>...</rss>"
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        # Mock feedparser response
        mock_feed = Mock()
        mock_feed.bozo = False
        mock_feed.entries = [
            {
                "link": "https://example.com/article1",
                "title": "Article 1",
                "summary": "Summary 1",
            },
            {
                "link": "https://example.com/article2",
                "title": "Article 2",
                "summary": "Summary 2",
            },
        ]
        mock_parse.return_value = mock_feed

        # Fetch feed
        source = RSSFeedSource("https://example.com/feed")
        entries = source.fetch()

        # Verify HTTP call
        mock_get.assert_called_once_with(
            "https://example.com/feed",
            timeout=30,
            follow_redirects=True
        )

        # Verify results
        assert len(entries) == 2
        assert entries[0].title == "Article 1"
        assert entries[1].title == "Article 2"

    @patch("pydigestor.sources.feeds.httpx.get")
    def test_fetch_http_error(self, mock_get):
        """Test handling HTTP errors."""
        # Mock HTTP error
        mock_get.side_effect = httpx.HTTPError("Connection failed")

        source = RSSFeedSource("https://example.com/feed")

        with pytest.raises(Exception):
            source.fetch()

    @patch("pydigestor.sources.feeds.httpx.get")
    @patch("pydigestor.sources.feeds.feedparser.parse")
    def test_fetch_with_bozo(self, mock_parse, mock_get):
        """Test handling malformed feed (bozo bit set)."""
        # Mock HTTP response
        mock_response = Mock()
        mock_response.content = b"<invalid>...</invalid>"
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        # Mock feedparser response with bozo bit
        mock_feed = Mock()
        mock_feed.bozo = True
        mock_feed.bozo_exception = Exception("Feed is malformed")
        mock_feed.entries = [
            {
                "link": "https://example.com/article1",
                "title": "Article 1",
            }
        ]
        mock_parse.return_value = mock_feed

        # Fetch should still work but log warning
        source = RSSFeedSource("https://example.com/feed")
        entries = source.fetch()

        # Should still return entries despite warning
        assert len(entries) == 1

    @patch("pydigestor.sources.feeds.httpx.get")
    @patch("pydigestor.sources.feeds.feedparser.parse")
    def test_fetch_filters_invalid_entries(self, mock_parse, mock_get):
        """Test that invalid entries are filtered out."""
        # Mock HTTP response
        mock_response = Mock()
        mock_response.content = b"<rss>...</rss>"
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        # Mock feedparser response with some invalid entries
        mock_feed = Mock()
        mock_feed.bozo = False
        mock_feed.entries = [
            {
                "link": "https://example.com/article1",
                "title": "Valid Article",
            },
            {
                # Missing link - should be filtered
                "title": "Invalid Article 1",
            },
            {
                # Missing title - should be filtered
                "link": "https://example.com/article2",
            },
            {
                "link": "https://example.com/article3",
                "title": "Another Valid Article",
            },
        ]
        mock_parse.return_value = mock_feed

        source = RSSFeedSource("https://example.com/feed")
        entries = source.fetch()

        # Should only get valid entries
        assert len(entries) == 2
        assert entries[0].title == "Valid Article"
        assert entries[1].title == "Another Valid Article"
