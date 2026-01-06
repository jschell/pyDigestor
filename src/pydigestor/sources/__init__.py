"""Feed sources for pyDigestor."""

from pydigestor.sources.extraction import ContentExtractor
from pydigestor.sources.feeds import FeedEntry, RSSFeedSource
from pydigestor.sources.reddit import QualityFilter, RedditFetcher, RedditPost

__all__ = [
    "FeedEntry",
    "RSSFeedSource",
    "ContentExtractor",
    "RedditFetcher",
    "RedditPost",
    "QualityFilter",
]
