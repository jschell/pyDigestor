"""Configuration management for pyDigestor."""

import json
from typing import Any

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Database
    database_url: str = Field(
        default="sqlite:///./data/pydigestor.db",
        description="SQLite database path",
    )

    # Feature Flags (Phase 1 - LLM features disabled)
    enable_triage: bool = Field(default=False, description="Enable LLM-based triage")
    enable_extraction: bool = Field(default=False, description="Enable LLM-based signal extraction")

    # LLM Configuration (Phase 2)
    anthropic_api_key: str | None = Field(default=None, description="Anthropic API key")
    triage_model: str = Field(
        default="claude-3-haiku-20240307", description="Model for triage"
    )
    extract_model: str = Field(
        default="claude-3-5-sonnet-20241022", description="Model for extraction"
    )

    # Feed Sources
    rss_feeds: list[str] = Field(
        default_factory=lambda: ["https://krebsonsecurity.com/feed/"],
        description="RSS/Atom feed URLs",
    )
    reddit_subreddits: list[str] = Field(
        default_factory=lambda: ["netsec"], description="Reddit subreddits to fetch"
    )

    # Reddit Configuration
    reddit_sort: str = Field(default="new", description="Reddit sort method (new, hot, top)")
    reddit_limit: int = Field(default=100, description="Max posts to fetch per subreddit")
    reddit_max_age_hours: int = Field(
        default=24, description="Maximum age of posts to process (hours)"
    )
    reddit_min_score: int = Field(
        default=0, description="Minimum score for posts (0 for fresh content)"
    )
    reddit_priority_hours: int = Field(
        default=6, description="Posts fresher than this get priority"
    )
    reddit_min_comments: int = Field(default=0, description="Minimum comments required")
    reddit_blocked_domains: list[str] = Field(
        default_factory=lambda: [
            "youtube.com",
            "youtu.be",
            "twitter.com",
            "x.com",
            "reddit.com",
            "tiktok.com",
            "instagram.com",
        ],
        description="Domains to block from Reddit links",
    )

    # Summarization
    auto_summarize: bool = Field(
        default=True, description="Auto-generate summaries during ingest"
    )
    summarization_method: str = Field(
        default="lexrank", description="Summarization method (lexrank, textrank, lsa)"
    )
    summary_min_content_length: int = Field(
        default=200, description="Minimum content length (chars) required for summarization"
    )
    summary_min_sentences: int = Field(
        default=3, description="Minimum sentences in summary"
    )
    summary_max_sentences: int = Field(
        default=8, description="Maximum sentences in summary"
    )
    summary_compression_ratio: float = Field(
        default=0.20, description="Target compression ratio for summaries"
    )

    # Content Extraction
    content_fetch_timeout: int = Field(
        default=10, description="Timeout for content fetching (seconds)"
    )
    content_max_retries: int = Field(
        default=2, description="Maximum retries for failed extractions"
    )
    enable_pattern_extraction: bool = Field(
        default=True, description="Enable pattern-based extraction"
    )

    # Application Settings
    log_level: str = Field(default="INFO", description="Logging level")
    enable_debug: bool = Field(default=False, description="Enable debug mode")

    @field_validator("rss_feeds", mode="before")
    @classmethod
    def parse_rss_feeds(cls, v: Any) -> list[str]:
        """Parse RSS feeds from JSON string or list."""
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return [v]
        return v

    @field_validator("reddit_subreddits", mode="before")
    @classmethod
    def parse_reddit_subreddits(cls, v: Any) -> list[str]:
        """Parse Reddit subreddits from JSON string or list."""
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return [v]
        return v

    @field_validator("reddit_blocked_domains", mode="before")
    @classmethod
    def parse_blocked_domains(cls, v: Any) -> list[str]:
        """Parse blocked domains from JSON string or list."""
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return [v]
        return v


# Global settings instance
settings = Settings()
