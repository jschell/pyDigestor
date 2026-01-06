"""Ingest step: Fetch feeds and store articles in database."""

from datetime import datetime, timezone
from typing import Optional

from rich.console import Console
from rich.table import Table
from sqlmodel import Session, select

from pydigestor.config import Settings
from pydigestor.database import get_session
from pydigestor.models import Article
from pydigestor.sources.feeds import FeedEntry, RSSFeedSource

console = Console()


class IngestStep:
    """Fetch RSS/Atom feeds and store articles in database."""

    def __init__(self, settings: Optional[Settings] = None):
        """
        Initialize ingest step.

        Args:
            settings: Application settings (defaults to Settings())
        """
        self.settings = settings or Settings()

    def run(self) -> dict:
        """
        Run the ingest step: fetch all configured feeds and store new articles.

        Returns:
            Dictionary with statistics:
                - total_fetched: Total entries fetched from feeds
                - new_articles: Number of new articles stored
                - duplicates: Number of duplicate articles skipped
                - errors: Number of feeds that failed
        """
        console.print("\n[bold]═══ Ingest Step ═══[/bold]\n")

        stats = {
            "total_fetched": 0,
            "new_articles": 0,
            "duplicates": 0,
            "errors": 0,
        }

        # Fetch entries from all RSS feeds
        all_entries = []
        for feed_url in self.settings.rss_feeds:
            try:
                source = RSSFeedSource(feed_url)
                entries = source.fetch()
                all_entries.extend(entries)
                stats["total_fetched"] += len(entries)
            except Exception as e:
                console.print(f"[red]✗[/red] Failed to fetch {feed_url}: {e}")
                stats["errors"] += 1

        console.print(f"\n[blue]Total entries fetched:[/blue] {stats['total_fetched']}")

        # Store entries in database
        if all_entries:
            session = next(get_session())
            for entry in all_entries:
                if self._store_article(session, entry):
                    stats["new_articles"] += 1
                else:
                    stats["duplicates"] += 1
            session.close()

        # Display results
        self._display_results(stats)

        return stats

    def _store_article(self, session: Session, entry: FeedEntry) -> bool:
        """
        Store a feed entry as an article in the database.

        Args:
            session: Database session
            entry: Feed entry to store

        Returns:
            True if article was stored (new), False if duplicate
        """
        # Check if article already exists
        existing = session.exec(
            select(Article).where(Article.source_id == entry.source_id)
        ).first()

        if existing:
            return False  # Duplicate

        # Create new article
        article = Article(
            source_id=entry.source_id,
            url=entry.url,
            title=entry.title,
            content=entry.content or "",
            summary=entry.summary,
            published_at=entry.published_at,
            fetched_at=datetime.now(timezone.utc),
            status="pending",
            meta={
                "author": entry.author,
                "tags": entry.tags,
            },
        )

        session.add(article)
        session.commit()
        console.print(f"[green]✓[/green] Stored: {entry.title[:60]}...")

        return True

    def _display_results(self, stats: dict) -> None:
        """Display ingest results in a table."""
        table = Table(title="Ingest Results", show_header=True)
        table.add_column("Metric", style="cyan")
        table.add_column("Count", style="green", justify="right")

        table.add_row("Total Fetched", str(stats["total_fetched"]))
        table.add_row("New Articles", str(stats["new_articles"]))
        table.add_row("Duplicates", str(stats["duplicates"]))
        table.add_row("Errors", str(stats["errors"]), style="red" if stats["errors"] > 0 else "green")

        console.print("\n")
        console.print(table)
        console.print("\n")
