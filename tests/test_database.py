"""Tests for database connection and operations."""

from pydigestor.models import Article


def test_database_connection(session):
    """Test that database session is created successfully."""
    assert session is not None
    # Should be able to query without errors
    result = session.query(Article).all()
    assert result == []


def test_database_session_commits(session, sample_article):
    """Test that database session can commit changes."""
    session.add(sample_article)
    session.commit()

    # Query back the article
    article = session.query(Article).filter(Article.source_id == "test-article-123").first()
    assert article is not None
    assert article.title == "Test Security Article"
