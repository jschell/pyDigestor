"""Pytest configuration and fixtures."""

import pytest
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from pydigestor.models import Article, Signal, TriageDecision  # noqa: F401


@pytest.fixture(name="engine")
def engine_fixture():
    """Create an in-memory SQLite engine for testing."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    return engine


@pytest.fixture(name="session")
def session_fixture(engine):
    """Create a database session for testing."""
    with Session(engine) as session:
        yield session


@pytest.fixture(name="sample_article")
def sample_article_fixture():
    """Create a sample article for testing."""
    from datetime import datetime

    return Article(
        source_id="test-article-123",
        url="https://example.com/article",
        title="Test Security Article",
        content="This is test content about a security vulnerability.",
        published_at=datetime(2026, 1, 5, 12, 0, 0),
        status="pending",
        meta={
            "source_type": "rss",
            "feed_url": "https://example.com/feed/",
        },
    )


@pytest.fixture(name="sample_signal")
def sample_signal_fixture(sample_article):
    """Create a sample signal for testing."""
    return Signal(
        article_id=sample_article.id,
        signal_type="vulnerability",
        content="CVE-2026-0001: Remote code execution in Example Software",
        confidence=0.95,
        meta={"severity": "critical", "cvss": 9.8},
    )


@pytest.fixture(name="sample_triage_decision")
def sample_triage_decision_fixture(sample_article):
    """Create a sample triage decision for testing."""
    return TriageDecision(
        article_id=sample_article.id,
        keep=True,
        reasoning="Relevant security content about a critical vulnerability",
        confidence=0.9,
    )
