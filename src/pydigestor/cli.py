"""Command-line interface for pyDigestor."""

import warnings

# Suppress SyntaxWarnings from newspaper3k library
warnings.filterwarnings("ignore", category=SyntaxWarning)

import typer
from rich.console import Console
from rich.table import Table

from pydigestor.config import settings
from pydigestor.database import get_session
from pydigestor.models import Article, Signal, TriageDecision
from pydigestor.steps.ingest import IngestStep
from pydigestor.steps.summarize import SummarizationStep
from pydigestor.search.fts import FTS5Search
from pydigestor.search.vector import VectorSearch
from pydigestor.search.hybrid import HybridSearch

app = typer.Typer(
    name="pydigestor",
    help="Feed aggregation and analysis pipeline for security content",
    add_completion=False,
)
console = Console()


@app.command()
def status():
    """Show pipeline status and statistics."""
    console.print("\n[bold cyan]pyDigestor Status[/bold cyan]\n")

    # Database connection test
    try:
        session = next(get_session())

        # Count articles
        articles_count = session.query(Article).count()
        pending_count = session.query(Article).filter(Article.status == "pending").count()
        processed_count = session.query(Article).filter(Article.status == "processed").count()

        # Count signals
        signals_count = session.query(Signal).count()

        # Count triage decisions
        triage_count = session.query(TriageDecision).count()

        # Create status table
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Metric", style="cyan")
        table.add_column("Count", justify="right", style="green")

        table.add_row("Total Articles", str(articles_count))
        table.add_row("  Pending", str(pending_count))
        table.add_row("  Processed", str(processed_count))
        table.add_row("Total Signals", str(signals_count))
        table.add_row("Triage Decisions", str(triage_count))

        console.print(table)

        # Configuration status
        console.print("\n[bold cyan]Configuration[/bold cyan]\n")
        config_table = Table(show_header=True, header_style="bold magenta")
        config_table.add_column("Setting", style="cyan")
        config_table.add_column("Value", style="yellow")

        config_table.add_row("RSS Feeds", str(len(settings.rss_feeds)))
        config_table.add_row("Reddit Subreddits", str(len(settings.reddit_subreddits)))
        config_table.add_row("Triage Enabled", "✓" if settings.enable_triage else "✗")
        config_table.add_row("Extraction Enabled", "✓" if settings.enable_extraction else "✗")
        config_table.add_row("Auto-Summarize", "✓" if settings.auto_summarize else "✗")
        config_table.add_row("Summarization Method", settings.summarization_method)

        console.print(config_table)
        console.print()

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(code=1)


@app.command()
def version():
    """Show version information."""
    console.print("[bold cyan]pyDigestor[/bold cyan] version [green]0.1.0[/green]")
    console.print("Phase 1: Core Pipeline (Development)")


@app.command()
def config():
    """Show current configuration."""
    console.print("\n[bold cyan]pyDigestor Configuration[/bold cyan]\n")

    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Setting", style="cyan", width=30)
    table.add_column("Value", style="yellow")

    # Database
    table.add_row("Database URL", settings.database_url)

    # Features
    table.add_row("Triage Enabled", str(settings.enable_triage))
    table.add_row("Extraction Enabled", str(settings.enable_extraction))

    # Feeds
    table.add_row("RSS Feeds", ", ".join(settings.rss_feeds))
    table.add_row("Reddit Subreddits", ", ".join(settings.reddit_subreddits))

    # Summarization
    table.add_row("Auto-Summarize", str(settings.auto_summarize))
    table.add_row("Summarization Method", settings.summarization_method)
    table.add_row("Summary Sentences", f"{settings.summary_min_sentences}-{settings.summary_max_sentences}")

    # Extraction
    table.add_row("Content Timeout", f"{settings.content_fetch_timeout}s")
    table.add_row("Pattern Extraction", str(settings.enable_pattern_extraction))

    # Application
    table.add_row("Log Level", settings.log_level)
    table.add_row("Debug Mode", str(settings.enable_debug))

    console.print(table)
    console.print()


@app.command()
def ingest(
    force_extraction: bool = typer.Option(
        False,
        "--force-extraction",
        "-f",
        help="Force content extraction even if content already exists"
    )
):
    """Fetch RSS/Atom feeds and store new articles in database."""
    try:
        step = IngestStep()
        stats = step.run(force_extraction=force_extraction)

        # Exit with error if there were issues
        if stats["errors"] > 0 and stats["new_articles"] == 0:
            console.print("[yellow]⚠[/yellow] Some feeds failed and no articles were stored")
            raise typer.Exit(code=1)

    except Exception as e:
        console.print(f"\n[bold red]Error:[/bold red] {e}")
        raise typer.Exit(code=1)


@app.command()
def summarize(
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Regenerate summaries for all articles (not just those missing summaries)"
    )
):
    """Generate extractive summaries for articles using local algorithms."""
    try:
        step = SummarizationStep()
        metrics = step.run(force=force)

        # Exit with error if nothing was summarized and there were errors
        if metrics["summarized"] == 0 and metrics["errors"] > 0:
            console.print("[yellow]⚠[/yellow] No articles were summarized and errors occurred")
            raise typer.Exit(code=1)

    except Exception as e:
        console.print(f"\n[bold red]Error:[/bold red] {e}")
        raise typer.Exit(code=1)


@app.command()
def search(
    query: str = typer.Argument(..., help="Search query (supports AND, OR, NOT, \"phrases\")"),
    limit: int = typer.Option(10, "--limit", "-n", help="Maximum number of results"),
):
    """Search articles using keyword search (FTS5)."""
    try:
        session = next(get_session())
        searcher = FTS5Search()

        # Get total count
        total = searcher.count_results(session, query)

        if total == 0:
            console.print(f"\n[yellow]No results found for:[/yellow] {query}\n")
            return

        # Get results
        results = searcher.search(session, query, limit=limit)

        # Display results
        console.print(f"\n[bold cyan]Search Results[/bold cyan] ({len(results)} of {total})")
        console.print(f"[dim]Query:[/dim] {query}\n")

        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("#", style="dim", width=3)
        table.add_column("Title", style="cyan", width=50)
        table.add_column("Snippet", style="white", width=60)
        table.add_column("Rank", justify="right", style="green", width=8)

        for idx, result in enumerate(results, 1):
            # Truncate title if too long
            title = result.title[:47] + "..." if len(result.title) > 50 else result.title
            # Clean snippet (remove extra newlines)
            snippet = " ".join(result.snippet.split())
            snippet = snippet[:57] + "..." if len(snippet) > 60 else snippet

            table.add_row(
                str(idx),
                title,
                snippet,
                f"{result.rank:.3f}"
            )

        console.print(table)
        console.print()

    except Exception as e:
        console.print(f"\n[bold red]Error:[/bold red] {e}")
        raise typer.Exit(code=1)


@app.command()
def semantic_search(
    query: str = typer.Argument(..., help="Search query for semantic similarity"),
    limit: int = typer.Option(10, "--limit", "-n", help="Maximum number of results"),
):
    """Search articles using semantic similarity (vector embeddings)."""
    try:
        session = next(get_session())
        searcher = VectorSearch()

        # Get results
        results = searcher.search_by_text(session, query, limit=limit)

        if not results:
            console.print(f"\n[yellow]No results found for:[/yellow] {query}\n")
            return

        # Display results
        console.print(f"\n[bold cyan]Semantic Search Results[/bold cyan] ({len(results)} results)")
        console.print(f"[dim]Query:[/dim] {query}\n")

        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("#", style="dim", width=3)
        table.add_column("Title", style="cyan", width=50)
        table.add_column("Summary", style="white", width=60)
        table.add_column("Distance", justify="right", style="green", width=10)

        for idx, result in enumerate(results, 1):
            # Truncate title and summary if too long
            title = result.title[:47] + "..." if len(result.title) > 50 else result.title
            summary = result.summary[:57] + "..." if len(result.summary) > 60 else result.summary

            table.add_row(
                str(idx),
                title,
                summary,
                f"{result.distance:.4f}"
            )

        console.print(table)
        console.print()

    except Exception as e:
        console.print(f"\n[bold red]Error:[/bold red] {e}")
        raise typer.Exit(code=1)


@app.command()
def similar(
    article_id: str = typer.Argument(..., help="Article ID to find similar articles for"),
    limit: int = typer.Option(10, "--limit", "-n", help="Maximum number of results"),
):
    """Find similar articles using vector similarity."""
    try:
        session = next(get_session())
        searcher = VectorSearch()

        # Get source article
        source_article = session.get(Article, article_id)
        if not source_article:
            console.print(f"\n[red]Error:[/red] Article {article_id} not found\n")
            raise typer.Exit(code=1)

        # Get similar articles
        results = searcher.find_similar(session, article_id, limit=limit)

        if not results:
            console.print(f"\n[yellow]No similar articles found[/yellow]\n")
            return

        # Display results
        console.print(f"\n[bold cyan]Similar Articles[/bold cyan] ({len(results)} results)")
        console.print(f"[dim]Source:[/dim] {source_article.title}\n")

        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("#", style="dim", width=3)
        table.add_column("Title", style="cyan", width=50)
        table.add_column("Summary", style="white", width=60)
        table.add_column("Distance", justify="right", style="green", width=10)

        for idx, result in enumerate(results, 1):
            # Truncate title and summary if too long
            title = result.title[:47] + "..." if len(result.title) > 50 else result.title
            summary = result.summary[:57] + "..." if len(result.summary) > 60 else result.summary

            table.add_row(
                str(idx),
                title,
                summary,
                f"{result.distance:.4f}"
            )

        console.print(table)
        console.print()

    except ValueError as e:
        console.print(f"\n[red]Error:[/red] {e}\n")
        raise typer.Exit(code=1)
    except Exception as e:
        console.print(f"\n[bold red]Error:[/bold red] {e}")
        raise typer.Exit(code=1)


@app.command()
def hybrid(
    query: str = typer.Argument(..., help="Search query (keyword + semantic)"),
    limit: int = typer.Option(10, "--limit", "-n", help="Maximum number of results"),
    fts_weight: float = typer.Option(0.5, "--fts-weight", help="Weight for FTS5 scores (0-1)"),
    vector_weight: float = typer.Option(0.5, "--vector-weight", help="Weight for vector scores (0-1)"),
):
    """Hybrid search combining keyword (FTS5) and semantic (vector) search with RRF."""
    try:
        session = next(get_session())
        searcher = HybridSearch()

        # Get results
        results = searcher.search(
            session,
            query,
            limit=limit,
            fts_weight=fts_weight,
            vector_weight=vector_weight
        )

        if not results:
            console.print(f"\n[yellow]No results found for:[/yellow] {query}\n")
            return

        # Display results
        console.print(f"\n[bold cyan]Hybrid Search Results[/bold cyan] ({len(results)} results)")
        console.print(f"[dim]Query:[/dim] {query}")
        console.print(f"[dim]Weights:[/dim] FTS={fts_weight:.1f}, Vector={vector_weight:.1f}\n")

        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("#", style="dim", width=3)
        table.add_column("Title", style="cyan", width=40)
        table.add_column("Snippet", style="white", width=45)
        table.add_column("RRF Score", justify="right", style="green", width=10)
        table.add_column("FTS", justify="right", style="blue", width=8)
        table.add_column("Vec", justify="right", style="yellow", width=8)

        for idx, result in enumerate(results, 1):
            # Truncate title and snippet if too long
            title = result.title[:37] + "..." if len(result.title) > 40 else result.title
            snippet = " ".join(result.snippet.split())  # Clean whitespace
            snippet = snippet[:42] + "..." if len(snippet) > 45 else snippet

            # Format FTS and vector scores
            fts_str = f"{result.fts_rank:.2f}" if result.fts_rank is not None else "-"
            vec_str = f"{result.vector_distance:.3f}" if result.vector_distance is not None else "-"

            table.add_row(
                str(idx),
                title,
                snippet,
                f"{result.rrf_score:.4f}",
                fts_str,
                vec_str
            )

        console.print(table)
        console.print()

    except Exception as e:
        console.print(f"\n[bold red]Error:[/bold red] {e}")
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
