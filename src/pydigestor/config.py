"""Configuration management for pyDigestor.

Supports loading configuration from:
1. config.toml - Non-secret settings (feeds, options, etc.)
2. .env - Secrets only (DATABASE_URL, API keys)
3. Environment variables - Override both (highest priority)

Priority: Environment variables > .env > config.toml > defaults
"""

import json
import tomllib
from pathlib import Path
from typing import Any

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from config.toml (non-secrets) and .env (secrets).

    Configuration loading order (higher priority overrides lower):
    1. Default values (defined in Field defaults)
    2. config.toml (non-secret configuration)
    3. .env file (secrets and overrides)
    4. Environment variables (highest priority)
    """

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

    def __init__(self, **kwargs):
        """
        Initialize settings, loading from config.toml if present.

        Loading order (later values override earlier):
        1. Default Field values
        2. config.toml (if exists)
        3. .env file (via Pydantic)
        4. Environment variables (via Pydantic)
        5. **kwargs passed to __init__
        """
        import sys
        import shutil

        # Auto-initialize config files from templates if they don't exist
        env_path = Path(".env")
        env_example_path = Path(".env.example")
        config_path = Path("config.toml")
        config_example_path = Path("config.example.toml")

        # Copy .env.example to .env if .env doesn't exist
        if not env_path.exists() and env_example_path.exists():
            try:
                shutil.copy(env_example_path, env_path)
                print(
                    f"ℹ️  Created .env from template (.env.example). "
                    f"Edit .env to add your secrets (API keys, database credentials).",
                    file=sys.stderr,
                )
            except Exception as e:
                print(f"Warning: Failed to copy .env.example to .env: {e}", file=sys.stderr)

        # Copy config.example.toml to config.toml if config.toml doesn't exist
        if not config_path.exists() and config_example_path.exists():
            try:
                shutil.copy(config_example_path, config_path)
                print(
                    f"ℹ️  Created config.toml from template (config.example.toml). "
                    f"Edit config.toml to customize feeds and settings.",
                    file=sys.stderr,
                )
            except Exception as e:
                print(f"Warning: Failed to copy config.example.toml to config.toml: {e}", file=sys.stderr)

        # Warn if .env contains non-secret configuration
        self._check_env_for_non_secrets(env_path, sys)

        # Load from config.toml (now guaranteed to exist if template was available)
        toml_data = {}

        if config_path.exists():
            try:
                with open(config_path, "rb") as f:
                    toml_config = tomllib.load(f)

                # Flatten TOML structure for Pydantic
                toml_data = self._flatten_toml(toml_config)
            except Exception as e:
                # If TOML parsing fails, log warning but continue
                # (allows fallback to .env and environment variables)
                print(f"Warning: Failed to load config.toml: {e}", file=sys.stderr)

        # Merge TOML data with kwargs (kwargs take precedence)
        # Pydantic will then override with .env and environment variables
        merged_data = {**toml_data, **kwargs}

        super().__init__(**merged_data)

    @staticmethod
    def _check_env_for_non_secrets(env_path: Path, sys) -> None:
        """
        Check if .env contains non-secret configuration and warn user.

        This helps users migrate from the old .env-only config to the new
        config.toml approach for non-secret settings.
        """
        if not env_path.exists():
            return

        # Non-secret keys that should be in config.toml instead
        non_secret_keys = {
            "RSS_FEEDS", "REDDIT_SUBREDDITS", "REDDIT_SORT", "REDDIT_LIMIT",
            "REDDIT_MAX_AGE_HOURS", "REDDIT_MIN_SCORE", "REDDIT_PRIORITY_HOURS",
            "REDDIT_MIN_COMMENTS", "REDDIT_BLOCKED_DOMAINS",
            "AUTO_SUMMARIZE", "SUMMARIZATION_METHOD", "SUMMARY_MIN_CONTENT_LENGTH",
            "SUMMARY_MIN_SENTENCES", "SUMMARY_MAX_SENTENCES", "SUMMARY_COMPRESSION_RATIO",
            "CONTENT_FETCH_TIMEOUT", "CONTENT_MAX_RETRIES", "ENABLE_PATTERN_EXTRACTION",
            "LOG_LEVEL", "ENABLE_DEBUG", "ENABLE_TRIAGE", "ENABLE_EXTRACTION",
            "TRIAGE_MODEL", "EXTRACT_MODEL",
        }

        try:
            with open(env_path) as f:
                env_lines = f.readlines()

            found_non_secrets = []
            for line in env_lines:
                line = line.strip()
                # Skip comments and empty lines
                if not line or line.startswith("#"):
                    continue

                # Extract key from KEY=value
                if "=" in line:
                    key = line.split("=")[0].strip()
                    if key in non_secret_keys:
                        found_non_secrets.append(key)

            if found_non_secrets:
                print(
                    f"\n⚠️  Warning: Your .env file contains non-secret configuration:\n"
                    f"   {', '.join(found_non_secrets[:3])}"
                    f"{' and ' + str(len(found_non_secrets) - 3) + ' more' if len(found_non_secrets) > 3 else ''}\n"
                    f"\n"
                    f"   These settings should be moved to config.toml for better organization.\n"
                    f"   For now, .env values will override config.toml (backward compatible).\n"
                    f"\n"
                    f"   Migration guide: docs/configuration-separation.md\n",
                    file=sys.stderr,
                )
        except Exception:
            # Silently fail - don't break config loading if we can't read .env
            pass

    @staticmethod
    def _flatten_toml(config: dict) -> dict:
        """
        Flatten TOML config structure to match Pydantic field names.

        Example:
            [feeds]
            rss_feeds = [...]

            Becomes: {"rss_feeds": [...]}
        """
        flat = {}

        # Feeds section
        if "feeds" in config:
            feeds = config["feeds"]
            if "rss_feeds" in feeds:
                flat["rss_feeds"] = feeds["rss_feeds"]
            if "reddit_subreddits" in feeds:
                flat["reddit_subreddits"] = feeds["reddit_subreddits"]

        # Reddit section
        if "reddit" in config:
            reddit = config["reddit"]
            if "sort" in reddit:
                flat["reddit_sort"] = reddit["sort"]
            if "limit" in reddit:
                flat["reddit_limit"] = reddit["limit"]
            if "max_age_hours" in reddit:
                flat["reddit_max_age_hours"] = reddit["max_age_hours"]
            if "min_score" in reddit:
                flat["reddit_min_score"] = reddit["min_score"]
            if "priority_hours" in reddit:
                flat["reddit_priority_hours"] = reddit["priority_hours"]
            if "min_comments" in reddit:
                flat["reddit_min_comments"] = reddit["min_comments"]
            if "blocked_domains" in reddit:
                flat["reddit_blocked_domains"] = reddit["blocked_domains"]

        # Summarization section
        if "summarization" in config:
            summ = config["summarization"]
            if "auto_summarize" in summ:
                flat["auto_summarize"] = summ["auto_summarize"]
            if "method" in summ:
                flat["summarization_method"] = summ["method"]
            if "min_content_length" in summ:
                flat["summary_min_content_length"] = summ["min_content_length"]
            if "min_sentences" in summ:
                flat["summary_min_sentences"] = summ["min_sentences"]
            if "max_sentences" in summ:
                flat["summary_max_sentences"] = summ["max_sentences"]
            if "compression_ratio" in summ:
                flat["summary_compression_ratio"] = summ["compression_ratio"]

        # Extraction section
        if "extraction" in config:
            ext = config["extraction"]
            if "enable_pattern_extraction" in ext:
                flat["enable_pattern_extraction"] = ext["enable_pattern_extraction"]
            if "fetch_timeout" in ext:
                flat["content_fetch_timeout"] = ext["fetch_timeout"]
            if "max_retries" in ext:
                flat["content_max_retries"] = ext["max_retries"]

        # Features section
        if "features" in config:
            feat = config["features"]
            if "enable_triage" in feat:
                flat["enable_triage"] = feat["enable_triage"]
            if "enable_extraction" in feat:
                flat["enable_extraction"] = feat["enable_extraction"]

        # LLM section
        if "llm" in config:
            llm = config["llm"]
            if "triage_model" in llm:
                flat["triage_model"] = llm["triage_model"]
            if "extract_model" in llm:
                flat["extract_model"] = llm["extract_model"]

        # Application section
        if "application" in config:
            app = config["application"]
            if "log_level" in app:
                flat["log_level"] = app["log_level"]
            if "enable_debug" in app:
                flat["enable_debug"] = app["enable_debug"]

        return flat


# Global settings instance
settings = Settings()
