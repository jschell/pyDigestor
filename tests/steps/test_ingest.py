"""Tests for ingest step."""

from datetime import datetime, timezone
from unittest.mock import Mock, patch

import pytest
from sqlmodel import select

from pydigestor.models import Article
from pydigestor.steps.ingest import IngestStep
from pydigestor.sources.feeds import FeedEntry


class TestIngestStep:
    """Tests for IngestStep class."""

    def test_init(self):
        """Test IngestStep initialization."""
        step = IngestStep()
        assert step.settings is not None

    def test_init_with_settings(self):
        """Test IngestStep with custom settings."""
        from pydigestor.config import Settings

        settings = Settings(rss_feeds=["https://example.com/feed"])
        step = IngestStep(settings=settings)

        assert step.settings == settings

    def test_store_article_new(self, session):
        """Test storing a new article."""
        step = IngestStep()

        entry = FeedEntry(
            source_id="rss:example.com:abc123",
            url="https://example.com/article",
            title="Test Article",
            content="Test content",
            summary="Test summary",
            published_at=datetime(2024, 1, 1, 12, 0, 0),
            author="John Doe",
            tags=["security", "test"],
        )

        # Store article
        result = step._store_article(session, entry)

        # Should return True (new article)
        assert result is True

        # Verify article in database
        article = session.exec(
            select(Article).where(Article.source_id == "rss:example.com:abc123")
        ).first()

        assert article is not None
        assert article.url == "https://example.com/article"
        assert article.title == "Test Article"
        assert article.content == "Test content"
        assert article.summary == "Test summary"
        assert article.status == "pending"
        assert article.meta["author"] == "John Doe"
        assert article.meta["tags"] == ["security", "test"]

    def test_store_article_duplicate(self, session):
        """Test that duplicate articles are skipped."""
        step = IngestStep()

        entry = FeedEntry(
            source_id="rss:example.com:abc123",
            url="https://example.com/article",
            title="Test Article",
            content="Test content",
        )

        # Store article first time
        result1 = step._store_article(session, entry)
        assert result1 is True

        # Try to store again (duplicate)
        result2 = step._store_article(session, entry)
        assert result2 is False

        # Verify only one article in database
        articles = session.exec(
            select(Article).where(Article.source_id == "rss:example.com:abc123")
        ).all()

        assert len(articles) == 1

    def test_store_article_no_content(self, session):
        """Test storing article with no content."""
        step = IngestStep()

        entry = FeedEntry(
            source_id="rss:example.com:abc123",
            url="https://example.com/article",
            title="Test Article",
            content=None,  # No content
        )

        result = step._store_article(session, entry)

        assert result is True

        article = session.exec(
            select(Article).where(Article.source_id == "rss:example.com:abc123")
        ).first()

        # Content should be empty string
        assert article.content == ""

    @patch("pydigestor.steps.ingest.RSSFeedSource")
    def test_run_success(self, mock_source_class, session):
        """Test successful ingest run."""
        # Mock RSSFeedSource
        mock_source = Mock()
        mock_entries = [
            FeedEntry(
                source_id="rss:example.com:abc123",
                url="https://example.com/article1",
                title="Article 1",
                content="Content 1",
            ),
            FeedEntry(
                source_id="rss:example.com:def456",
                url="https://example.com/article2",
                title="Article 2",
                content="Content 2",
            ),
        ]
        mock_source.fetch.return_value = mock_entries
        mock_source_class.return_value = mock_source

        # Run ingest
        from pydigestor.config import Settings
        settings = Settings(rss_feeds=["https://example.com/feed"])
        step = IngestStep(settings=settings)

        stats = step.run(session=session)

        # Verify stats
        assert stats["total_fetched"] == 2
        assert stats["new_articles"] == 2
        assert stats["duplicates"] == 0
        assert stats["errors"] == 0

        # Verify articles in database
        articles = session.exec(select(Article)).all()
        assert len(articles) == 2

    @patch("pydigestor.steps.ingest.RSSFeedSource")
    def test_run_with_duplicates(self, mock_source_class, session):
        """Test ingest run with duplicate detection."""
        # Pre-populate database with one article
        existing = Article(
            source_id="rss:example.com:abc123",
            url="https://example.com/article1",
            title="Existing Article",
            content="Existing content",
            fetched_at=datetime.now(timezone.utc),
            status="pending",
        )
        session.add(existing)
        session.commit()

        # Mock RSSFeedSource with one duplicate and one new
        mock_source = Mock()
        mock_entries = [
            FeedEntry(
                source_id="rss:example.com:abc123",  # Duplicate
                url="https://example.com/article1",
                title="Article 1",
                content="Content 1",
            ),
            FeedEntry(
                source_id="rss:example.com:def456",  # New
                url="https://example.com/article2",
                title="Article 2",
                content="Content 2",
            ),
        ]
        mock_source.fetch.return_value = mock_entries
        mock_source_class.return_value = mock_source

        # Run ingest
        from pydigestor.config import Settings
        settings = Settings(rss_feeds=["https://example.com/feed"])
        step = IngestStep(settings=settings)

        stats = step.run(session=session)

        # Verify stats
        assert stats["total_fetched"] == 2
        assert stats["new_articles"] == 1  # Only one new
        assert stats["duplicates"] == 1  # One duplicate
        assert stats["errors"] == 0

        # Verify total articles in database
        articles = session.exec(select(Article)).all()
        assert len(articles) == 2  # Original + 1 new

    @patch("pydigestor.steps.ingest.RSSFeedSource")
    def test_run_with_errors(self, mock_source_class, session):
        """Test ingest run with feed errors."""
        # Mock RSSFeedSource to raise error
        mock_source = Mock()
        mock_source.fetch.side_effect = Exception("Feed error")
        mock_source_class.return_value = mock_source

        # Run ingest
        from pydigestor.config import Settings
        settings = Settings(rss_feeds=["https://example.com/feed"])
        step = IngestStep(settings=settings)

        stats = step.run(session=session)

        # Verify stats
        assert stats["total_fetched"] == 0
        assert stats["new_articles"] == 0
        assert stats["duplicates"] == 0
        assert stats["errors"] == 1

    @patch("pydigestor.steps.ingest.RSSFeedSource")
    def test_run_multiple_feeds(self, mock_source_class, session):
        """Test ingest run with multiple feeds."""
        # Mock RSSFeedSource to return different entries per feed
        def mock_fetch_side_effect(*args, **kwargs):
            # Different entries for each instantiation
            mock = Mock()
            if not hasattr(mock_fetch_side_effect, "call_count"):
                mock_fetch_side_effect.call_count = 0

            if mock_fetch_side_effect.call_count == 0:
                # First feed
                mock.fetch.return_value = [
                    FeedEntry(
                        source_id="rss:feed1.com:abc",
                        url="https://feed1.com/article1",
                        title="Feed 1 Article",
                        content="Content 1",
                    )
                ]
            else:
                # Second feed
                mock.fetch.return_value = [
                    FeedEntry(
                        source_id="rss:feed2.com:def",
                        url="https://feed2.com/article2",
                        title="Feed 2 Article",
                        content="Content 2",
                    )
                ]

            mock_fetch_side_effect.call_count += 1
            return mock

        mock_source_class.side_effect = mock_fetch_side_effect

        # Run ingest with two feeds
        from pydigestor.config import Settings
        settings = Settings(
            rss_feeds=["https://feed1.com/feed", "https://feed2.com/feed"]
        )
        step = IngestStep(settings=settings)

        stats = step.run(session=session)

        # Verify stats
        assert stats["total_fetched"] == 2
        assert stats["new_articles"] == 2
        assert stats["errors"] == 0

        # Verify both articles in database
        articles = session.exec(select(Article)).all()
        assert len(articles) == 2
