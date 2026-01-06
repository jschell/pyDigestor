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


if __name__ == "__main__":
    app()
