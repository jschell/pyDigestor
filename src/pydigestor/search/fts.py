"""FTS5 full-text search implementation."""

from dataclasses import dataclass

from sqlalchemy import text
from sqlmodel import Session


@dataclass
class SearchResult:
    """FTS5 search result."""

    article_id: str
    title: str
    snippet: str
    rank: float


class FTS5Search:
    """Full-text search using SQLite FTS5."""

    def search(
        self, session: Session, query: str, limit: int = 10
    ) -> list[SearchResult]:
        """
        Search articles using FTS5.

        Args:
            session: Database session
            query: Search query (FTS5 syntax supported: AND, OR, NOT, "phrase")
            limit: Max results to return

        Returns:
            List of ranked search results with snippets

        Example:
            >>> searcher = FTS5Search()
            >>> results = searcher.search(session, "SQL injection", limit=5)
            >>> for r in results:
            ...     print(f"{r.title}: {r.snippet}")
        """
        # FTS5 query with snippet generation
        sql = text(
            """
            SELECT
                fts.article_id,
                articles.title,
                snippet(articles_fts, 1, '<mark>', '</mark>', '...', 40) as snippet,
                fts.rank
            FROM articles_fts fts
            JOIN articles ON articles.id = fts.article_id
            WHERE articles_fts MATCH :query
            ORDER BY rank
            LIMIT :limit
        """
        )

        results = session.execute(sql, {"query": query, "limit": limit}).fetchall()

        return [
            SearchResult(
                article_id=row[0], title=row[1], snippet=row[2], rank=row[3]
            )
            for row in results
        ]

    def count_results(self, session: Session, query: str) -> int:
        """
        Count total results for a query without retrieving them.

        Args:
            session: Database session
            query: Search query

        Returns:
            Total count of matching articles
        """
        sql = text(
            """
            SELECT COUNT(*)
            FROM articles_fts
            WHERE articles_fts MATCH :query
        """
        )

        result = session.execute(sql, {"query": query}).fetchone()
        return result[0] if result else 0
