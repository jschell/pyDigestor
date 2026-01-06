"""Feed sources for pyDigestor."""

from pydigestor.sources.extraction import ContentExtractor
from pydigestor.sources.feeds import FeedEntry, RSSFeedSource

__all__ = ["FeedEntry", "RSSFeedSource", "ContentExtractor"]
