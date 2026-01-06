"""Tests for Reddit integration."""

import time
from datetime import datetime, timezone
from unittest.mock import Mock, patch

import pytest

from pydigestor.sources.reddit import QualityFilter, RedditFetcher, RedditPost


class TestRedditPost:
    """Tests for RedditPost dataclass."""

    def test_create_reddit_post(self):
        """Test creating a RedditPost."""
        post = RedditPost(
            id="abc123",
            title="Test Post",
            url="https://example.com",
            permalink="/r/test/comments/abc123",
            created_utc=1234567890.0,
            score=42,
            author="testuser",
            subreddit="test",
            is_self=False,
            domain="example.com",
        )

        assert post.id == "abc123"
        assert post.title == "Test Post"
        assert post.url == "https://example.com"
        assert post.score == 42
        assert post.author == "testuser"
        assert post.subreddit == "test"
        assert not post.is_self
        assert post.domain == "example.com"

    def test_self_post(self):
        """Test creating a self post."""
        post = RedditPost(
            id="abc123",
            title="Self Post",
            url="https://reddit.com/r/test/comments/abc123",
            permalink="/r/test/comments/abc123",
            created_utc=1234567890.0,
            score=10,
            author="testuser",
            subreddit="test",
            is_self=True,
            selftext="This is the post body",
        )

        assert post.is_self
        assert post.selftext == "This is the post body"


class TestQualityFilter:
    """Tests for QualityFilter class."""

    def test_init(self):
        """Test QualityFilter initialization."""
        filter = QualityFilter(max_age_hours=48, min_score=10)
        assert filter.max_age_hours == 48
        assert filter.min_score == 10
        assert "youtube.com" in filter.blocked_domains
        assert "twitter.com" in filter.blocked_domains

    def test_init_custom_blocked_domains(self):
        """Test adding custom blocked domains."""
        filter = QualityFilter(blocked_domains=["example.com", "test.com"])
        assert "example.com" in filter.blocked_domains
        assert "test.com" in filter.blocked_domains
        # Should still have defaults
        assert "youtube.com" in filter.blocked_domains

    def test_should_process_fresh_post(self):
        """Test that fresh posts pass the filter."""
        filter = QualityFilter(max_age_hours=24, min_score=0)

        post = {
            "created_utc": time.time() - 3600,  # 1 hour ago
            "score": 5,
            "url": "https://example.com/article",
            "is_self": False,
        }

        assert filter.should_process(post)

    def test_should_process_old_post(self):
        """Test that old posts are rejected."""
        filter = QualityFilter(max_age_hours=24, min_score=0)

        post = {
            "created_utc": time.time() - (48 * 3600),  # 48 hours ago
            "score": 10,
            "url": "https://example.com/article",
            "is_self": False,
        }

        assert not filter.should_process(post)

    def test_should_process_low_score(self):
        """Test that low-score posts are rejected."""
        filter = QualityFilter(max_age_hours=24, min_score=10)

        post = {
            "created_utc": time.time() - 3600,  # 1 hour ago
            "score": 5,  # Below minimum
            "url": "https://example.com/article",
            "is_self": False,
        }

        assert not filter.should_process(post)

    def test_should_process_blocked_domain(self):
        """Test that posts from blocked domains are rejected."""
        filter = QualityFilter(max_age_hours=24, min_score=0)

        post = {
            "created_utc": time.time() - 3600,
            "score": 10,
            "url": "https://www.youtube.com/watch?v=123",
            "is_self": False,
        }

        assert not filter.should_process(post)

    def test_should_process_blocked_domain_without_www(self):
        """Test that blocked domains work without www prefix."""
        filter = QualityFilter(max_age_hours=24, min_score=0)

        post = {
            "created_utc": time.time() - 3600,
            "score": 10,
            "url": "https://twitter.com/user/status/123",
            "is_self": False,
        }

        assert not filter.should_process(post)

    def test_should_process_self_post_with_content(self):
        """Test that self posts with content pass."""
        filter = QualityFilter(max_age_hours=24, min_score=0)

        post = {
            "created_utc": time.time() - 3600,
            "score": 5,
            "url": "",
            "is_self": True,
            "selftext": "This is a long enough self post with plenty of content to be considered quality.",
        }

        assert filter.should_process(post)

    def test_should_process_self_post_too_short(self):
        """Test that short self posts are rejected."""
        filter = QualityFilter(max_age_hours=24, min_score=0)

        post = {
            "created_utc": time.time() - 3600,
            "score": 5,
            "url": "",
            "is_self": True,
            "selftext": "Too short",  # Less than 50 chars
        }

        assert not filter.should_process(post)

    def test_calculate_priority_fresh(self):
        """Test priority calculation for fresh posts."""
        filter = QualityFilter(max_age_hours=24)

        post = {
            "created_utc": time.time(),  # Just now
        }

        priority = filter.calculate_priority(post)
        assert priority >= 0.99  # Should be close to 1.0

    def test_calculate_priority_old(self):
        """Test priority calculation for old posts."""
        filter = QualityFilter(max_age_hours=24)

        post = {
            "created_utc": time.time() - (24 * 3600),  # 24 hours ago
        }

        priority = filter.calculate_priority(post)
        assert priority <= 0.01  # Should be close to 0.0

    def test_calculate_priority_middle(self):
        """Test priority calculation for medium-age posts."""
        filter = QualityFilter(max_age_hours=24)

        post = {
            "created_utc": time.time() - (12 * 3600),  # 12 hours ago
        }

        priority = filter.calculate_priority(post)
        assert 0.4 < priority < 0.6  # Should be around 0.5


class TestRedditFetcher:
    """Tests for RedditFetcher class."""

    def test_init(self):
        """Test RedditFetcher initialization."""
        fetcher = RedditFetcher(user_agent="TestAgent/1.0", rate_limit=60)
        assert fetcher.user_agent == "TestAgent/1.0"
        assert fetcher.rate_limiter.calls_per_minute == 60
        assert fetcher.base_url == "https://www.reddit.com"

    def test_init_default(self):
        """Test RedditFetcher with default settings."""
        fetcher = RedditFetcher()
        assert fetcher.user_agent == "pyDigestor/0.1.0"
        assert fetcher.rate_limiter.calls_per_minute == 30

    @patch("pydigestor.sources.reddit.httpx.get")
    def test_fetch_subreddit_success(self, mock_get):
        """Test successful subreddit fetch."""
        # Mock response
        mock_response = Mock()
        mock_response.json.return_value = {
            "data": {
                "children": [
                    {
                        "kind": "t3",
                        "data": {
                            "id": "abc123",
                            "title": "Test Post",
                            "url": "https://example.com/article",
                            "permalink": "/r/test/comments/abc123",
                            "created_utc": time.time(),
                            "score": 10,
                            "author": "testuser",
                            "is_self": False,
                        },
                    }
                ]
            }
        }
        mock_get.return_value = mock_response

        fetcher = RedditFetcher()
        entries = fetcher.fetch_subreddit("test", limit=10)

        assert len(entries) == 1
        assert entries[0].title == "Test Post"
        assert entries[0].url == "https://example.com/article"
        assert "r/test" in entries[0].tags

    @patch("pydigestor.sources.reddit.httpx.get")
    def test_fetch_subreddit_with_filter(self, mock_get):
        """Test subreddit fetch with quality filter."""
        # Mock response with one good post and one bad post
        mock_response = Mock()
        mock_response.json.return_value = {
            "data": {
                "children": [
                    {
                        "kind": "t3",
                        "data": {
                            "id": "abc123",
                            "title": "Good Post",
                            "url": "https://example.com/article",
                            "permalink": "/r/test/comments/abc123",
                            "created_utc": time.time(),
                            "score": 10,
                            "author": "testuser",
                            "is_self": False,
                        },
                    },
                    {
                        "kind": "t3",
                        "data": {
                            "id": "def456",
                            "title": "YouTube Post",
                            "url": "https://youtube.com/watch?v=123",
                            "permalink": "/r/test/comments/def456",
                            "created_utc": time.time(),
                            "score": 100,
                            "author": "testuser",
                            "is_self": False,
                        },
                    },
                ]
            }
        }
        mock_get.return_value = mock_response

        quality_filter = QualityFilter(max_age_hours=24)
        fetcher = RedditFetcher()
        entries = fetcher.fetch_subreddit("test", limit=10, quality_filter=quality_filter)

        # Only the non-YouTube post should pass
        assert len(entries) == 1
        assert entries[0].title == "Good Post"

    @patch("pydigestor.sources.reddit.httpx.get")
    def test_fetch_subreddit_self_post(self, mock_get):
        """Test fetching self posts."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "data": {
                "children": [
                    {
                        "kind": "t3",
                        "data": {
                            "id": "abc123",
                            "title": "Self Post",
                            "url": "https://reddit.com/r/test/comments/abc123",
                            "permalink": "/r/test/comments/abc123",
                            "created_utc": time.time(),
                            "score": 10,
                            "author": "testuser",
                            "is_self": True,
                            "selftext": "This is the post body text",
                        },
                    }
                ]
            }
        }
        mock_get.return_value = mock_response

        fetcher = RedditFetcher()
        entries = fetcher.fetch_subreddit("test")

        assert len(entries) == 1
        assert entries[0].title == "Self Post"
        assert entries[0].url == "https://www.reddit.com/r/test/comments/abc123"
        assert entries[0].content == "This is the post body text"

    @patch("pydigestor.sources.reddit.httpx.get")
    def test_fetch_subreddit_http_error(self, mock_get):
        """Test handling of HTTP errors."""
        import httpx

        mock_get.side_effect = httpx.HTTPError("Network error")

        fetcher = RedditFetcher()
        entries = fetcher.fetch_subreddit("test")

        assert len(entries) == 0

    @patch("pydigestor.sources.reddit.httpx.get")
    def test_fetch_subreddit_json_error(self, mock_get):
        """Test handling of malformed JSON."""
        mock_response = Mock()
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_get.return_value = mock_response

        fetcher = RedditFetcher()
        entries = fetcher.fetch_subreddit("test")

        assert len(entries) == 0

    @patch("pydigestor.sources.reddit.httpx.get")
    def test_fetch_subreddit_empty_response(self, mock_get):
        """Test handling of empty response."""
        mock_response = Mock()
        mock_response.json.return_value = {"data": {"children": []}}
        mock_get.return_value = mock_response

        fetcher = RedditFetcher()
        entries = fetcher.fetch_subreddit("test")

        assert len(entries) == 0

    def test_post_to_feed_entry_link_post(self):
        """Test converting a link post to FeedEntry."""
        fetcher = RedditFetcher()

        post = {
            "id": "abc123",
            "title": "Test Article",
            "url": "https://example.com/article",
            "permalink": "/r/test/comments/abc123",
            "created_utc": 1234567890.0,
            "score": 42,
            "author": "testuser",
            "is_self": False,
        }

        entry = fetcher._post_to_feed_entry(post, "test")

        assert entry is not None
        assert entry.source_id == "reddit:test:abc123"
        assert entry.title == "Test Article"
        assert entry.url == "https://example.com/article"
        assert entry.author == "u/testuser"
        assert "r/test" in entry.tags
        assert entry.content == ""  # Link posts have no content

    def test_post_to_feed_entry_self_post(self):
        """Test converting a self post to FeedEntry."""
        fetcher = RedditFetcher()

        post = {
            "id": "abc123",
            "title": "Self Post",
            "url": "https://reddit.com/r/test/comments/abc123",
            "permalink": "/r/test/comments/abc123",
            "created_utc": 1234567890.0,
            "score": 10,
            "author": "testuser",
            "is_self": True,
            "selftext": "This is the post body",
        }

        entry = fetcher._post_to_feed_entry(post, "test")

        assert entry is not None
        assert entry.source_id == "reddit:test:abc123"
        assert entry.url == "https://www.reddit.com/r/test/comments/abc123"
        assert entry.content == "This is the post body"

    def test_post_to_feed_entry_missing_id(self):
        """Test that posts without ID are rejected."""
        fetcher = RedditFetcher()

        post = {
            "title": "Test Post",
            "url": "https://example.com",
            "permalink": "/r/test/comments/abc123",
            "created_utc": time.time(),
            "author": "testuser",
            "is_self": False,
        }

        entry = fetcher._post_to_feed_entry(post, "test")
        assert entry is None

    def test_post_to_feed_entry_missing_title(self):
        """Test that posts without title are rejected."""
        fetcher = RedditFetcher()

        post = {
            "id": "abc123",
            "url": "https://example.com",
            "permalink": "/r/test/comments/abc123",
            "created_utc": time.time(),
            "author": "testuser",
            "is_self": False,
        }

        entry = fetcher._post_to_feed_entry(post, "test")
        assert entry is None

    def test_post_to_feed_entry_timestamp_conversion(self):
        """Test timestamp conversion."""
        fetcher = RedditFetcher()

        post = {
            "id": "abc123",
            "title": "Test Post",
            "url": "https://example.com",
            "permalink": "/r/test/comments/abc123",
            "created_utc": 1234567890.0,
            "author": "testuser",
            "is_self": False,
        }

        entry = fetcher._post_to_feed_entry(post, "test")

        assert entry is not None
        assert entry.published_at is not None
        assert isinstance(entry.published_at, datetime)
        assert entry.published_at.tzinfo == timezone.utc
