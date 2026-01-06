"""Tests for summarization step."""

from datetime import datetime
from unittest.mock import Mock, patch

import pytest
from sqlmodel import select

from pydigestor.models import Article
from pydigestor.steps.summarize import SummarizationStep


class TestSummarizationStep:
    """Tests for SummarizationStep class."""

    def test_init(self):
        """Test SummarizationStep initialization."""
        step = SummarizationStep()
        assert step.metrics is not None
        assert step.metrics["total_articles"] == 0
        assert step.metrics["summarized"] == 0
        assert step.metrics["skipped"] == 0
        assert step.metrics["errors"] == 0

    def test_ensure_nltk_data(self):
        """Test NLTK data download."""
        # This should run without errors
        step = SummarizationStep()
        step._ensure_nltk_data()

    def test_get_summarizer_lexrank(self):
        """Test getting LexRank summarizer."""
        from pydigestor.config import Settings
        from pydigestor.steps.summarize import LexRankSummarizer

        # Mock settings
        with patch("pydigestor.steps.summarize.settings") as mock_settings:
            mock_settings.summarization_method = "lexrank"

            step = SummarizationStep()
            summarizer = step._get_summarizer()

            assert isinstance(summarizer, LexRankSummarizer)

    def test_get_summarizer_textrank(self):
        """Test getting TextRank summarizer."""
        from pydigestor.config import Settings
        from pydigestor.steps.summarize import TextRankSummarizer

        with patch("pydigestor.steps.summarize.settings") as mock_settings:
            mock_settings.summarization_method = "textrank"

            step = SummarizationStep()
            summarizer = step._get_summarizer()

            assert isinstance(summarizer, TextRankSummarizer)

    def test_get_summarizer_lsa(self):
        """Test getting LSA summarizer."""
        from pydigestor.config import Settings
        from pydigestor.steps.summarize import LsaSummarizer

        with patch("pydigestor.steps.summarize.settings") as mock_settings:
            mock_settings.summarization_method = "lsa"

            step = SummarizationStep()
            summarizer = step._get_summarizer()

            assert isinstance(summarizer, LsaSummarizer)

    def test_get_summarizer_invalid_method(self):
        """Test getting summarizer with invalid method."""
        with patch("pydigestor.steps.summarize.settings") as mock_settings:
            mock_settings.summarization_method = "invalid_method"

            step = SummarizationStep()

            with pytest.raises(ValueError, match="Unsupported summarization method"):
                step._get_summarizer()

    def test_generate_summary_success(self):
        """Test successful summary generation."""
        step = SummarizationStep()

        # Long content with multiple distinct sentences for better summarization
        content = """
        Cybersecurity researchers at a major security firm have discovered a new critical vulnerability in widely-used enterprise software that could impact millions of users worldwide. The vulnerability, which has been assigned a CVE identifier, allows remote attackers to execute arbitrary code on affected systems without requiring any form of authentication or user interaction. Security experts from multiple organizations recommend immediate patching to prevent potential exploitation of this serious security flaw. The discovered flaw affects millions of computer systems worldwide and could lead to significant data breaches if left unpatched by organizations. Companies and organizations are being urged to update their systems as soon as possible to mitigate the substantial risk posed by this vulnerability. The vulnerability was responsibly disclosed to the software vendor several months before the public announcement to allow time for patch development. Security patches have now been released by the vendor and are available for immediate download from the official website and through automated update mechanisms.
        """

        with patch("pydigestor.steps.summarize.settings") as mock_settings:
            mock_settings.summarization_method = "lexrank"
            mock_settings.summary_min_sentences = 2
            mock_settings.summary_max_sentences = 3
            mock_settings.summary_compression_ratio = 0.20

            summary = step._generate_summary(content)

            # Summary should be generated
            assert summary is not None
            assert len(summary) > 0
            # Summary should be shorter than original
            assert len(summary) < len(content)

    def test_generate_summary_empty_content(self):
        """Test summary generation with empty content."""
        step = SummarizationStep()

        summary = step._generate_summary("")

        # Should handle empty content gracefully
        assert summary is None or summary == ""

    def test_generate_summary_short_content(self):
        """Test summary generation with very short content."""
        step = SummarizationStep()

        content = "This is too short."

        with patch("pydigestor.steps.summarize.settings") as mock_settings:
            mock_settings.summarization_method = "lexrank"
            mock_settings.summary_min_sentences = 3
            mock_settings.summary_max_sentences = 5
            mock_settings.summary_compression_ratio = 0.20

            summary = step._generate_summary(content)

            # May return None or the original content
            # depending on how the summarizer handles it
            assert summary is None or isinstance(summary, str)

    def test_run_no_articles(self, session):
        """Test running summarization with no articles in database."""
        step = SummarizationStep()

        with patch("pydigestor.steps.summarize.engine", session.get_bind()):
            metrics = step.run()

        assert metrics["total_articles"] == 0
        assert metrics["summarized"] == 0
        assert metrics["skipped"] == 0
        assert metrics["errors"] == 0

    def test_run_articles_without_content(self, session):
        """Test running summarization on articles without content."""
        # Create article without content
        article = Article(
            source_id="test-article-1",
            url="https://example.com/article1",
            title="Test Article 1",
            content=None,  # No content
            summary=None,
            published_at=datetime(2026, 1, 5, 12, 0, 0),
            status="pending",
        )
        session.add(article)
        session.commit()

        step = SummarizationStep()

        with patch("pydigestor.steps.summarize.engine", session.get_bind()):
            metrics = step.run()

        # Should not summarize articles without content
        assert metrics["total_articles"] == 0
        assert metrics["summarized"] == 0

    def test_run_articles_with_existing_summary(self, session):
        """Test that articles with existing summaries are skipped by default."""
        # Create article with existing summary
        article = Article(
            source_id="test-article-1",
            url="https://example.com/article1",
            title="Test Article 1",
            content="Long content about security vulnerabilities and exploits.",
            summary="Existing summary",
            published_at=datetime(2026, 1, 5, 12, 0, 0),
            status="pending",
        )
        session.add(article)
        session.commit()

        step = SummarizationStep()

        with patch("pydigestor.steps.summarize.engine", session.get_bind()):
            metrics = step.run(force=False)

        # Should skip articles with existing summaries
        assert metrics["total_articles"] == 0
        assert metrics["summarized"] == 0

    def test_run_force_regenerate_summaries(self, session):
        """Test force mode regenerates all summaries."""
        # Create article with existing summary
        content = """
        Cybersecurity researchers at a major security firm have discovered a new critical vulnerability in widely-used enterprise software that could impact millions of users worldwide. The vulnerability, which has been assigned a CVE identifier, allows remote attackers to execute arbitrary code on affected systems without requiring any form of authentication or user interaction. Security experts from multiple organizations recommend immediate patching to prevent potential exploitation of this serious security flaw. The discovered flaw affects millions of computer systems worldwide and could lead to significant data breaches if left unpatched by organizations. Companies and organizations are being urged to update their systems as soon as possible to mitigate the substantial risk posed by this vulnerability.
        """

        article = Article(
            source_id="test-article-1",
            url="https://example.com/article1",
            title="Test Article 1",
            content=content,
            summary="Old summary",
            published_at=datetime(2026, 1, 5, 12, 0, 0),
            status="pending",
        )
        session.add(article)
        session.commit()

        step = SummarizationStep()

        with patch("pydigestor.steps.summarize.engine", session.get_bind()):
            with patch("pydigestor.steps.summarize.settings") as mock_settings:
                mock_settings.summarization_method = "lexrank"
                mock_settings.summary_min_sentences = 2
                mock_settings.summary_max_sentences = 3
                mock_settings.summary_compression_ratio = 0.20

                metrics = step.run(force=True)

        # Should regenerate summary even though one exists
        assert metrics["total_articles"] == 1
        assert metrics["summarized"] == 1

        # Verify summary was updated
        session.refresh(article)
        assert article.summary != "Old summary"
        assert article.summary is not None
        assert len(article.summary) > 0

    def test_run_skip_short_content(self, session):
        """Test that articles with short content are skipped."""
        # Create article with short content (<200 chars)
        article = Article(
            source_id="test-article-1",
            url="https://example.com/article1",
            title="Test Article 1",
            content="Too short.",  # Only 10 characters
            summary=None,
            published_at=datetime(2026, 1, 5, 12, 0, 0),
            status="pending",
        )
        session.add(article)
        session.commit()

        step = SummarizationStep()

        with patch("pydigestor.steps.summarize.engine", session.get_bind()):
            metrics = step.run()

        # Should skip short content
        assert metrics["total_articles"] == 1
        assert metrics["summarized"] == 0
        assert metrics["skipped"] == 1

    def test_run_successful_summarization(self, session):
        """Test successful summarization of multiple articles."""
        # Create articles without summaries
        content = """
        Cybersecurity researchers at a major security firm have discovered a new critical vulnerability in widely-used enterprise software that could impact millions of users worldwide. The vulnerability, which has been assigned a CVE identifier, allows remote attackers to execute arbitrary code on affected systems without requiring any form of authentication or user interaction. Security experts from multiple organizations recommend immediate patching to prevent potential exploitation of this serious security flaw. The discovered flaw affects millions of computer systems worldwide and could lead to significant data breaches if left unpatched by organizations. Companies and organizations are being urged to update their systems as soon as possible to mitigate the substantial risk posed by this vulnerability.
        """

        article1 = Article(
            source_id="test-article-1",
            url="https://example.com/article1",
            title="Test Article 1",
            content=content,
            summary=None,
            published_at=datetime(2026, 1, 5, 12, 0, 0),
            status="pending",
        )

        article2 = Article(
            source_id="test-article-2",
            url="https://example.com/article2",
            title="Test Article 2",
            content=content,
            summary="",  # Empty summary
            published_at=datetime(2026, 1, 5, 13, 0, 0),
            status="pending",
        )

        session.add(article1)
        session.add(article2)
        session.commit()

        step = SummarizationStep()

        with patch("pydigestor.steps.summarize.engine", session.get_bind()):
            with patch("pydigestor.steps.summarize.settings") as mock_settings:
                mock_settings.summarization_method = "lexrank"
                mock_settings.summary_min_sentences = 2
                mock_settings.summary_max_sentences = 3
                mock_settings.summary_compression_ratio = 0.20

                metrics = step.run()

        # Should summarize both articles
        assert metrics["total_articles"] == 2
        assert metrics["summarized"] == 2
        assert metrics["skipped"] == 0
        assert metrics["errors"] == 0

        # Verify summaries were added
        session.refresh(article1)
        session.refresh(article2)

        assert article1.summary is not None
        assert len(article1.summary) > 0

        assert article2.summary is not None
        assert len(article2.summary) > 0

    def test_run_handles_summarization_errors(self, session):
        """Test that summarization errors are handled gracefully."""
        # Create article
        article = Article(
            source_id="test-article-1",
            url="https://example.com/article1",
            title="Test Article 1",
            content="Long enough content to not be skipped for length reasons. " * 20,
            summary=None,
            published_at=datetime(2026, 1, 5, 12, 0, 0),
            status="pending",
        )
        session.add(article)
        session.commit()

        step = SummarizationStep()

        # Mock _generate_summary to raise an exception
        with patch.object(step, "_generate_summary", side_effect=Exception("Test error")):
            with patch("pydigestor.steps.summarize.engine", session.get_bind()):
                metrics = step.run()

        # Should handle error and continue
        assert metrics["total_articles"] == 1
        assert metrics["summarized"] == 0
        assert metrics["errors"] == 1
