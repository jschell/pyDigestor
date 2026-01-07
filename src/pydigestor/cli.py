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
from pydigestor.search.fts import FTS5Search, FTS5SearchError
from pydigestor.search.tfidf import TfidfSearch

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

    except FTS5SearchError as e:
        console.print(f"\n[bold yellow]Invalid Query Syntax:[/bold yellow]\n{e}\n")
        raise typer.Exit(code=1)
    except Exception as e:
        console.print(f"\n[bold red]Error:[/bold red] {e}")
        raise typer.Exit(code=1)


@app.command()
def build_tfidf_index(
    max_features: int = typer.Option(5000, "--max-features", help="Maximum vocabulary size"),
    min_df: int = typer.Option(2, "--min-df", help="Minimum document frequency"),
):
    """Build TF-IDF index from all articles in database."""
    try:
        console.print("\n[bold]Building TF-IDF Index[/bold]\n")

        session = next(get_session())
        searcher = TfidfSearch()

        # Build index
        stats = searcher.build_index(session, min_df=min_df, max_features=max_features)

        if "error" in stats:
            console.print(f"[red]Error:[/red] {stats['error']}\n")
            raise typer.Exit(code=1)

        # Display statistics
        console.print(f"[green]✓[/green] Indexed {stats['num_articles']} articles")
        console.print(f"[green]✓[/green] Vocabulary size: {stats['vocabulary_size']} terms")
        console.print(f"[dim]Index saved to: {searcher.index_path}[/dim]\n")

        # Show top terms
        console.print("[bold]Top 10 Terms by Importance:[/bold]")
        top_terms = searcher.get_top_terms(10)
        for term, score in top_terms:
            console.print(f"  • {term}: {score:.4f}")
        console.print()

    except Exception as e:
        console.print(f"\n[bold red]Error:[/bold red] {e}")
        raise typer.Exit(code=1)


@app.command()
def tfidf_search(
    query: str = typer.Argument(..., help="Search query for ranked retrieval"),
    limit: int = typer.Option(10, "--limit", "-n", help="Maximum number of results"),
    min_score: float = typer.Option(0.0, "--min-score", help="Minimum similarity score (0-1)"),
):
    """Search articles using TF-IDF ranked retrieval."""
    try:
        session = next(get_session())
        searcher = TfidfSearch()

        # Search
        results = searcher.search(session, query, limit=limit, min_score=min_score)

        if not results:
            console.print(f"\n[yellow]No results found for:[/yellow] {query}\n")
            return

        # Display results
        console.print(f"\n[bold cyan]TF-IDF Search Results[/bold cyan] ({len(results)} results)")
        console.print(f"[dim]Query:[/dim] {query}\n")

        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("#", style="dim", width=3)
        table.add_column("Title", style="cyan", width=50)
        table.add_column("Summary", style="white", width=60)
        table.add_column("Score", justify="right", style="green", width=8)

        for idx, result in enumerate(results, 1):
            # Truncate title and summary if too long
            title = result.title[:47] + "..." if len(result.title) > 50 else result.title
            summary = result.summary[:57] + "..." if len(result.summary) > 60 else result.summary

            table.add_row(
                str(idx),
                title,
                summary,
                f"{result.score:.3f}"
            )

        console.print(table)
        console.print()

    except ValueError as e:
        console.print(f"\n[yellow]Note:[/yellow] {e}")
        console.print("[dim]Run 'pydigestor build-tfidf-index' to create the index.[/dim]\n")
        raise typer.Exit(code=1)
    except Exception as e:
        console.print(f"\n[bold red]Error:[/bold red] {e}")
        raise typer.Exit(code=1)


@app.command()
def tfidf_terms(
    n: int = typer.Option(20, "--limit", "-n", help="Number of top terms to show"),
):
    """Show top terms in TF-IDF vocabulary (useful for understanding corpus)."""
    try:
        searcher = TfidfSearch()

        top_terms = searcher.get_top_terms(n)

        console.print(f"\n[bold cyan]Top {n} Terms by Average TF-IDF Score[/bold cyan]\n")
        console.print("[dim]These terms are most important/distinctive in your corpus.[/dim]\n")

        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Rank", style="dim", width=5)
        table.add_column("Term", style="cyan", width=40)
        table.add_column("Avg Score", justify="right", style="green", width=12)

        for idx, (term, score) in enumerate(top_terms, 1):
            table.add_row(str(idx), term, f"{score:.6f}")

        console.print(table)
        console.print()

    except ValueError as e:
        console.print(f"\n[yellow]Note:[/yellow] {e}")
        console.print("[dim]Run 'pydigestor build-tfidf-index' to create the index.[/dim]\n")
        raise typer.Exit(code=1)
    except Exception as e:
        console.print(f"\n[bold red]Error:[/bold red] {e}")
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
