"""Tests for database models."""

from datetime import datetime
from uuid import UUID

from pydigestor.models import Article, Signal, TriageDecision


def test_article_model_creation():
    """Test Article model can be created with required fields."""
    article = Article(
        source_id="test-123",
        url="https://example.com",
        title="Test Article",
        content="Test content",
    )

    assert article.source_id == "test-123"
    assert article.url == "https://example.com"
    assert article.title == "Test Article"
    assert article.content == "Test content"
    assert article.status == "pending"  # Default value
    assert isinstance(article.id, UUID)
    assert isinstance(article.fetched_at, datetime)
    assert article.meta == {}  # Default empty dict


def test_article_with_meta():
    """Test Article model stores meta correctly."""
    article = Article(
        source_id="test-456",
        url="https://example.com",
        title="Test",
        meta={"source_type": "rss", "feed_url": "https://example.com/feed/"},
    )

    assert article.meta["source_type"] == "rss"
    assert article.meta["feed_url"] == "https://example.com/feed/"


def test_article_database_insert(session, sample_article):
    """Test Article can be inserted into database."""
    session.add(sample_article)
    session.commit()

    # Query back
    article = session.query(Article).filter(Article.source_id == "test-article-123").first()
    assert article is not None
    assert article.title == "Test Security Article"
    assert article.meta["source_type"] == "rss"


def test_signal_model_creation(sample_article):
    """Test Signal model can be created."""
    signal = Signal(
        article_id=sample_article.id,
        signal_type="vulnerability",
        content="Test vulnerability",
        confidence=0.95,
    )

    assert signal.article_id == sample_article.id
    assert signal.signal_type == "vulnerability"
    assert signal.content == "Test vulnerability"
    assert signal.confidence == 0.95
    assert isinstance(signal.id, UUID)
    assert isinstance(signal.created_at, datetime)


def test_signal_database_insert(session, sample_article, sample_signal):
    """Test Signal can be inserted with foreign key."""
    # Insert article first
    session.add(sample_article)
    session.commit()

    # Insert signal
    session.add(sample_signal)
    session.commit()

    # Query back
    signal = session.query(Signal).filter(Signal.article_id == sample_article.id).first()
    assert signal is not None
    assert signal.signal_type == "vulnerability"
    assert signal.confidence == 0.95


def test_triage_decision_model_creation(sample_article):
    """Test TriageDecision model can be created."""
    decision = TriageDecision(
        article_id=sample_article.id,
        keep=True,
        reasoning="Relevant content",
        confidence=0.9,
    )

    assert decision.article_id == sample_article.id
    assert decision.keep is True
    assert decision.reasoning == "Relevant content"
    assert decision.confidence == 0.9
    assert isinstance(decision.id, UUID)
    assert isinstance(decision.created_at, datetime)


def test_triage_decision_database_insert(session, sample_article, sample_triage_decision):
    """Test TriageDecision can be inserted with foreign key."""
    # Insert article first
    session.add(sample_article)
    session.commit()

    # Insert decision
    session.add(sample_triage_decision)
    session.commit()

    # Query back
    decision = (
        session.query(TriageDecision)
        .filter(TriageDecision.article_id == sample_article.id)
        .first()
    )
    assert decision is not None
    assert decision.keep is True
    assert decision.confidence == 0.9
