"""Ingest step: Fetch feeds and store articles in database."""

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from rich.console import Console
from rich.table import Table
from sqlmodel import Session, select

from pydigestor.config import Settings
from pydigestor.database import get_session
from pydigestor.models import Article
from pydigestor.sources.extraction import ContentExtractor
from pydigestor.sources.feeds import FeedEntry, RSSFeedSource
from pydigestor.sources.reddit import QualityFilter, RedditFetcher

console = Console()


class IngestStep:
    """Fetch RSS/Atom feeds and Reddit posts, then store articles in database."""

    def __init__(self, settings: Optional[Settings] = None):
        """
        Initialize ingest step.

        Args:
            settings: Application settings (defaults to Settings())
        """
        self.settings = settings or Settings()

    def run(self, session: Optional[Session] = None, force_extraction: bool = False) -> dict:
        """
        Run the ingest step: fetch all configured RSS feeds and Reddit posts, then store new articles.

        Args:
            session: Optional database session (for testing). If not provided, creates a new session.
            force_extraction: Force content extraction even if content already exists.

        Returns:
            Dictionary with statistics:
                - total_fetched: Total entries fetched from all sources (RSS + Reddit)
                - new_articles: Number of new articles stored
                - duplicates: Number of duplicate articles skipped
                - errors: Number of sources that failed
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

        # Fetch entries from Reddit subreddits
        if self.settings.reddit_subreddits:
            console.print(f"\n[blue]Fetching from Reddit...[/blue]")

            # Create quality filter
            quality_filter = QualityFilter(
                max_age_hours=self.settings.reddit_max_age_hours,
                min_score=self.settings.reddit_min_score,
                blocked_domains=self.settings.reddit_blocked_domains,
            )

            # Fetch from each subreddit
            fetcher = RedditFetcher()
            for subreddit in self.settings.reddit_subreddits:
                try:
                    entries = fetcher.fetch_subreddit(
                        subreddit=subreddit,
                        sort=self.settings.reddit_sort,
                        limit=self.settings.reddit_limit,
                        quality_filter=quality_filter,
                    )
                    all_entries.extend(entries)
                    stats["total_fetched"] += len(entries)
                except Exception as e:
                    console.print(f"[red]✗[/red] Failed to fetch /r/{subreddit}: {e}")
                    stats["errors"] += 1

        console.print(f"\n[blue]Total entries fetched:[/blue] {stats['total_fetched']}")

        # Extract content from URLs
        if all_entries and self.settings.enable_pattern_extraction:
            console.print(f"\n[blue]Extracting content...[/blue]")
            extractor = ContentExtractor(
                timeout=self.settings.content_fetch_timeout,
                max_retries=self.settings.content_max_retries,
            )

            for entry in all_entries:
                # Extract if forced, or if content is empty/short
                if force_extraction or not entry.content or len(entry.content) < 200:
                    content, resolved_url = extractor.extract(entry.url)
                    if content:
                        entry.content = content
                        entry.url = resolved_url  # Use resolved URL as source of truth

            # Add extraction metrics to stats
            extraction_metrics = extractor.get_metrics()
            stats["extraction"] = extraction_metrics
            console.print(
                f"[green]✓[/green] Content extraction: {extraction_metrics['success_rate']}% success rate "
                f"({extraction_metrics['trafilatura_success'] + extraction_metrics['newspaper_success']}"
                f"/{extraction_metrics['total_attempts']})"
            )

        # Store entries in database
        new_article_ids: list[UUID] = []
        if all_entries:
            # Use provided session or create new one
            db_session = session or next(get_session())
            should_close = session is None  # Only close if we created it

            try:
                for entry in all_entries:
                    article_id = self._store_article(db_session, entry)
                    if article_id:
                        stats["new_articles"] += 1
                        new_article_ids.append(article_id)
                    else:
                        stats["duplicates"] += 1

                # Auto-generate summaries for new articles if enabled
                if self.settings.auto_summarize and new_article_ids:
                    self._auto_summarize(db_session, new_article_ids)

            finally:
                if should_close:
                    db_session.close()

        # Display results
        self._display_results(stats)

        return stats

    def _store_article(self, session: Session, entry: FeedEntry) -> UUID | None:
        """
        Store a feed entry as an article in the database.

        Args:
            session: Database session
            entry: Feed entry to store

        Returns:
            Article ID if article was stored (new), None if duplicate
        """
        # Check if article already exists
        existing = session.exec(
            select(Article).where(Article.source_id == entry.source_id)
        ).first()

        if existing:
            return None  # Duplicate

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
        session.refresh(article)  # Get the generated ID
        console.print(f"[green]✓[/green] Stored: {entry.title[:60]}...")

        return article.id

    def _auto_summarize(self, session: Session, article_ids: list[UUID]) -> None:
        """
        Auto-generate summaries for newly ingested articles.

        Args:
            session: Database session
            article_ids: List of article IDs to summarize
        """
        from pydigestor.steps.summarize import SummarizationStep

        console.print(f"\n[blue]Auto-summarizing {len(article_ids)} new article(s)...[/blue]")

        # Get articles with content that need summarization
        articles = session.exec(
            select(Article)
            .where(Article.id.in_(article_ids))
            .where(Article.content.is_not(None))
            .where((Article.summary.is_(None)) | (Article.summary == ""))
        ).all()

        if not articles:
            console.print("[dim]No articles need summarization.[/dim]")
            return

        # Create summarizer and generate summaries
        summarizer = SummarizationStep()
        summarized_count = 0

        for article in articles:
            # Skip if content is too short
            if len(article.content.strip()) < self.settings.summary_min_content_length:
                continue

            # Generate summary
            summary = summarizer._generate_summary(article.content)
            if summary:
                article.summary = summary
                session.add(article)
                summarized_count += 1

        # Commit all summaries
        session.commit()

        if summarized_count > 0:
            console.print(
                f"[green]✓[/green] Auto-summarized {summarized_count} article(s)"
            )

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
