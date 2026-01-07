"""Summarization step for generating article summaries."""

import nltk
from rich.console import Console
from rich.table import Table
from sqlmodel import Session, select
from sumy.nlp.tokenizers import Tokenizer
from sumy.parsers.plaintext import PlaintextParser
from sumy.summarizers.lsa import LsaSummarizer
from sumy.summarizers.lex_rank import LexRankSummarizer
from sumy.summarizers.text_rank import TextRankSummarizer

from pydigestor.config import settings
from pydigestor.database import engine
from pydigestor.models import Article

console = Console()


class SummarizationStep:
    """
    Generate extractive summaries for articles using local algorithms.

    Supports multiple summarization methods:
    - lexrank: Graph-based ranking of sentences by importance
    - textrank: Graph-based ranking using PageRank algorithm
    - lsa: Latent Semantic Analysis for topic-based summarization
    """

    def __init__(self):
        """Initialize summarization step and download NLTK data if needed."""
        self._ensure_nltk_data()
        self.metrics = {
            "total_articles": 0,
            "summarized": 0,
            "skipped": 0,
            "errors": 0,
        }

    def _ensure_nltk_data(self):
        """Download required NLTK data packages."""
        try:
            # Check if punkt tokenizer is available
            nltk.data.find("tokenizers/punkt")
        except LookupError:
            console.print("[yellow]Downloading NLTK punkt tokenizer...[/yellow]")
            nltk.download("punkt", quiet=True)

        try:
            # Check if punkt_tab tokenizer is available (newer NLTK versions)
            nltk.data.find("tokenizers/punkt_tab")
        except LookupError:
            console.print("[yellow]Downloading NLTK punkt_tab tokenizer...[/yellow]")
            nltk.download("punkt_tab", quiet=True)

        try:
            # Check if stopwords are available
            nltk.data.find("corpora/stopwords")
        except LookupError:
            console.print("[yellow]Downloading NLTK stopwords...[/yellow]")
            nltk.download("stopwords", quiet=True)

    def _get_summarizer(self):
        """
        Get the appropriate summarizer based on configuration.

        Returns:
            Sumy summarizer instance

        Raises:
            ValueError: If summarization method is not supported
        """
        method = settings.summarization_method.lower()

        if method == "lexrank":
            return LexRankSummarizer()
        elif method == "textrank":
            return TextRankSummarizer()
        elif method == "lsa":
            return LsaSummarizer()
        else:
            raise ValueError(
                f"Unsupported summarization method: {method}. "
                f"Use 'lexrank', 'textrank', or 'lsa'."
            )

    def _generate_summary(self, content: str) -> str | None:
        """
        Generate summary for article content.

        Args:
            content: Full article text

        Returns:
            Generated summary or None if failed
        """
        try:
            # Parse content
            parser = PlaintextParser.from_string(content, Tokenizer("english"))

            # Get summarizer
            summarizer = self._get_summarizer()

            # Calculate number of sentences (between min and max)
            document_sentences = len(list(parser.document.sentences))
            target_sentences = min(
                settings.summary_max_sentences,
                max(
                    settings.summary_min_sentences,
                    int(document_sentences * settings.summary_compression_ratio),
                ),
            )

            # Generate summary
            summary_sentences = summarizer(parser.document, target_sentences)

            # Combine sentences into text
            summary = " ".join(str(sentence) for sentence in summary_sentences)

            return summary.strip() if summary else None

        except Exception as e:
            console.print(f"[yellow]⚠[/yellow] Summarization failed: {e}")
            return None

    def run(self, force: bool = False) -> dict:
        """
        Run summarization step on articles.

        Args:
            force: If True, regenerate summaries for all articles with content.
                   If False, only generate summaries for articles without one.

        Returns:
            Dictionary with summarization metrics
        """
        console.print("\n[bold cyan]═══ Summarization Step ═══[/bold cyan]\n")

        with Session(engine) as session:
            # Build query based on force flag
            if force:
                # Regenerate all summaries
                query = select(Article).where(Article.content.is_not(None))
                console.print("[yellow]Force mode:[/yellow] Regenerating all summaries...")
            else:
                # Only summarize articles without summaries
                query = (
                    select(Article)
                    .where(Article.content.is_not(None))
                    .where((Article.summary.is_(None)) | (Article.summary == ""))
                )
                console.print("Summarizing articles without summaries...")

            articles = session.exec(query).all()

            if not articles:
                console.print("[dim]No articles to summarize.[/dim]")
                return self.metrics

            self.metrics["total_articles"] = len(articles)
            console.print(f"Found {len(articles)} article(s) to summarize\n")

            # Process each article
            for article in articles:
                try:
                    # Skip if content is too short
                    if len(article.content.strip()) < settings.summary_min_content_length:
                        console.print(
                            f"[dim]⊘ Skipping (too short): {article.title[:60]}...[/dim]"
                        )
                        self.metrics["skipped"] += 1
                        continue

                    # Generate summary
                    summary = self._generate_summary(article.content)

                    if summary:
                        # Update article
                        article.summary = summary
                        session.add(article)
                        self.metrics["summarized"] += 1

                        console.print(
                            f"[green]✓[/green] Summarized: {article.title[:60]}..."
                        )
                    else:
                        console.print(
                            f"[yellow]⚠[/yellow] Failed to summarize: {article.title[:60]}..."
                        )
                        self.metrics["errors"] += 1

                except Exception as e:
                    console.print(
                        f"[red]✗[/red] Error summarizing {article.title[:60]}...: {e}"
                    )
                    self.metrics["errors"] += 1

            # Commit all changes
            session.commit()

        # Display results
        self._display_results()

        return self.metrics

    def _display_results(self):
        """Display summarization results in a table."""
        console.print()
        table = Table(title="Summarization Results", show_header=True, header_style="bold cyan")
        table.add_column("Metric", style="dim")
        table.add_column("Count", justify="right")

        table.add_row("Total Articles", str(self.metrics["total_articles"]))
        table.add_row("Summarized", str(self.metrics["summarized"]))
        table.add_row("Skipped (too short)", str(self.metrics["skipped"]))
        table.add_row("Errors", str(self.metrics["errors"]))

        # Calculate success rate
        if self.metrics["total_articles"] > 0:
            success_rate = (
                self.metrics["summarized"] / self.metrics["total_articles"]
            ) * 100
            table.add_row("Success Rate", f"{success_rate:.1f}%")

        console.print(table)
