"""Test full ingestion flow with mock data and real extraction."""
from datetime import datetime, UTC
from uuid import uuid4

from sqlmodel import Session, select

from sqlalchemy import text

from pydigestor.database import engine
from pydigestor.models import Article
from pydigestor.sources.extraction import ContentExtractor


def test_database_storage():
    """Test article storage and retrieval."""
    print("\n=== Testing Database Storage ===")

    with Session(engine) as session:
        # Create test article
        article = Article(
            source_id=f"test_{uuid4()}",
            url="https://github.com/anthropics/anthropic-sdk-python",
            title="Test GitHub Repository",
            content="Test content for database storage.",
            summary="Test summary",
            published_at=datetime.now(UTC),
            status="processed",
            meta={"source": "test", "pattern": "github"}
        )

        session.add(article)
        session.commit()
        session.refresh(article)

        print(f"✓ Stored article: {article.id}")
        print(f"  Title: {article.title}")
        print(f"  URL: {article.url}")
        print(f"  Meta: {article.meta}")

        # Retrieve article
        retrieved = session.get(Article, article.id)
        assert retrieved is not None
        assert retrieved.title == article.title
        print(f"✓ Retrieved article successfully")

        # Count total articles
        count = session.exec(select(Article)).all()
        print(f"✓ Total articles in database: {len(count)}")

        return article.id


def test_github_extraction():
    """Test GitHub pattern extraction with real URL."""
    print("\n=== Testing GitHub Pattern Extraction ===")

    extractor = ContentExtractor()

    # Test GitHub URL
    url = "https://github.com/anthropics/anthropic-sdk-python"
    print(f"Extracting from: {url}")

    content, resolved_url = extractor.extract(url)

    if content:
        print(f"✓ Extraction succeeded")
        print(f"  Content length: {len(content)} chars")
        print(f"  Resolved URL: {resolved_url}")
        print(f"  Content preview: {content[:200]}...")

        # Check metrics
        metrics = extractor.get_metrics()
        print(f"\n  Metrics:")
        print(f"    Total attempts: {metrics['total_attempts']}")
        print(f"    Success rate: {metrics['success_rate']}%")
        if 'pattern_extractions' in metrics and metrics['pattern_extractions']:
            print(f"    Pattern extractions: {metrics['pattern_extractions']}")

        return content
    else:
        print(f"✗ Extraction failed")
        return None


def test_fts5_search(article_id: str):
    """Test FTS5 full-text search."""
    print("\n=== Testing FTS5 Search ===")

    with Session(engine) as session:
        # Simple FTS5 query
        query = text("""
        SELECT
            a.id,
            a.title,
            snippet(articles_fts, 1, '<mark>', '</mark>', '...', 40) as snippet
        FROM articles_fts fts
        JOIN articles a ON a.id = fts.article_id
        WHERE articles_fts MATCH :search_term
        LIMIT 5
        """)

        search_term = "python"
        print(f"Searching for: '{search_term}'")

        results = session.exec(query, params={"search_term": search_term}).all()

        if results:
            print(f"✓ Found {len(results)} results:")
            for result in results:
                print(f"  - {result[1][:50]}...")
                print(f"    {result[2]}")
        else:
            print(f"  No results found for '{search_term}'")

            # Try alternative search
            search_term = "test"
            print(f"\nTrying alternative search: '{search_term}'")
            results = session.exec(query, params={"search_term": search_term}).all()

            if results:
                print(f"✓ Found {len(results)} results:")
                for result in results:
                    print(f"  - {result[1][:50]}...")
            else:
                print(f"  No results found")


def test_summarization():
    """Test local summarization."""
    print("\n=== Testing Summarization ===")

    from pydigestor.steps.summarize import SummarizationStep

    # Sample content (needs to be long enough for summarization)
    content = """
    The Anthropic Python library provides convenient access to the Anthropic REST API
    from any Python 3.9+ application. It includes type definitions for all request
    params and response fields, and offers both synchronous and asynchronous clients
    powered by httpx.

    The library is designed to be easy to use while providing full access to the API.
    It supports streaming responses, automatic retries, and comprehensive error handling.

    Installation is simple via pip, and the library works with both synchronous and
    asynchronous code patterns. It includes built-in support for all Anthropic models
    including Claude 3.5 Sonnet and Claude 3 Opus.

    The SDK provides type hints for better IDE support and includes helper utilities
    for common tasks like prompt caching and tool use. It's actively maintained by
    the Anthropic team and follows semantic versioning.
    """

    print(f"Content length: {len(content)} chars")

    try:
        step = SummarizationStep()
        summary = step._generate_summary(content)

        if summary:
            print(f"✓ Summary generated:")
            print(f"  {summary}")
            print(f"  Summary length: {len(summary)} chars")
        else:
            print(f"✗ Summarization failed (content may be too short)")
    except Exception as e:
        print(f"✗ Summarization error: {e}")


def test_pattern_metrics():
    """Test pattern extraction metrics tracking."""
    print("\n=== Testing Pattern Metrics ===")

    extractor = ContentExtractor()

    # Test multiple URLs
    test_urls = [
        "https://github.com/anthropics/anthropic-sdk-python",
        "https://arxiv.org/abs/2501.12345",  # Will convert to PDF
        "https://example.com/article.pdf",
    ]

    for url in test_urls:
        print(f"\nTesting: {url}")
        content, resolved = extractor.extract(url)
        if content:
            print(f"  ✓ Extracted {len(content)} chars")
        else:
            print(f"  ✗ Extraction failed")

    # Show metrics
    metrics = extractor.get_metrics()
    print(f"\nFinal Metrics:")
    print(f"  Total attempts: {metrics['total_attempts']}")
    print(f"  Success rate: {metrics['success_rate']}%")
    print(f"  Pattern usage: {metrics.get('pattern_extractions', {})}")


def main():
    """Run all tests."""
    print("=" * 60)
    print("pyDigestor Ingestion Flow Test")
    print("=" * 60)

    # Test 1: Database storage
    article_id = test_database_storage()

    # Test 2: GitHub extraction
    test_github_extraction()

    # Test 3: FTS5 search
    test_fts5_search(article_id)

    # Test 4: Summarization
    test_summarization()

    # Test 5: Pattern metrics
    test_pattern_metrics()

    print("\n" + "=" * 60)
    print("All tests complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
