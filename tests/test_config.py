"""Tests for configuration management."""

from pydigestor.config import Settings


def test_settings_default_values():
    """Test Settings has correct default values."""
    settings = Settings()

    assert settings.enable_triage is False
    assert settings.enable_extraction is False
    assert settings.summarization_method == "lexrank"
    assert settings.summary_min_sentences == 3
    assert settings.summary_max_sentences == 8
    assert settings.content_fetch_timeout == 10
    assert settings.log_level == "INFO"


def test_settings_parse_json_lists():
    """Test Settings can parse JSON string lists."""
    settings = Settings(
        rss_feeds='["https://feed1.com", "https://feed2.com"]',
        reddit_subreddits='["netsec", "blueteamsec"]',
    )

    assert len(settings.rss_feeds) == 2
    assert "https://feed1.com" in settings.rss_feeds
    assert len(settings.reddit_subreddits) == 2
    assert "netsec" in settings.reddit_subreddits


def test_settings_accepts_list_directly():
    """Test Settings accepts lists directly without JSON parsing."""
    settings = Settings(
        rss_feeds=["https://feed1.com"],
        reddit_subreddits=["netsec"],
    )

    assert settings.rss_feeds == ["https://feed1.com"]
    assert settings.reddit_subreddits == ["netsec"]
