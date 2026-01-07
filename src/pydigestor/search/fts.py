"""FTS5 full-text search implementation."""

import re
from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from sqlmodel import Session


@dataclass
class SearchResult:
    """FTS5 search result."""

    article_id: str
    title: str
    snippet: str
    rank: float


class FTS5SearchError(Exception):
    """Exception raised for FTS5 query syntax errors."""

    pass


class FTS5Search:
    """Full-text search using SQLite FTS5."""

    @staticmethod
    def sanitize_query(query: str) -> str:
        """
        Sanitize user query for FTS5 to prevent syntax errors.

        Handles common issues:
        - Trailing operators (-, +)
        - Unmatched quotes
        - Special characters that break FTS5

        Args:
            query: Raw user query

        Returns:
            Sanitized query safe for FTS5

        Example:
            >>> FTS5Search.sanitize_query("CVE-")
            "CVE"
            >>> FTS5Search.sanitize_query('SQL "injection')
            'SQL "injection"'
        """
        # Remove trailing operators
        query = re.sub(r'[-+*]\s*$', '', query)

        # Remove leading operators
        query = re.sub(r'^\s*[-+*]', '', query)

        # Balance quotes
        if query.count('"') % 2 != 0:
            query += '"'

        # Remove operators next to each other
        query = re.sub(r'(AND|OR|NOT)\s+(AND|OR|NOT)', r'\1', query, flags=re.IGNORECASE)

        # Clean up whitespace
        query = ' '.join(query.split())

        return query if query else '*'

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

        Raises:
            FTS5SearchError: If query has invalid FTS5 syntax

        Example:
            >>> searcher = FTS5Search()
            >>> results = searcher.search(session, "SQL injection", limit=5)
            >>> for r in results:
            ...     print(f"{r.title}: {r.snippet}")

        FTS5 Query Syntax:
            - Basic: "SQL injection" (implicit AND)
            - AND: "SQL AND injection"
            - OR: "SQL OR python"
            - NOT: "SQL NOT MySQL"
            - Phrases: "\"SQL injection\""
            - Prefix: "vuln*" (matches vulnerability, vulnerable, etc.)
            - Column: title:CVE (search only in title)
        """
        # Sanitize query to prevent common syntax errors
        sanitized_query = self.sanitize_query(query)

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

        try:
            results = session.execute(
                sql, {"query": sanitized_query, "limit": limit}
            ).fetchall()
        except OperationalError as e:
            error_msg = str(e)
            if "fts5: syntax error" in error_msg:
                raise FTS5SearchError(
                    f"Invalid FTS5 query syntax: '{query}'\n\n"
                    f"Tips:\n"
                    f"  - Use quotes for phrases: \"SQL injection\"\n"
                    f"  - Use * for prefix matching: vuln*\n"
                    f"  - Combine with AND/OR: SQL AND injection\n"
                    f"  - Exclude terms with NOT: SQL NOT MySQL\n"
                    f"  - Search specific column: title:CVE\n\n"
                    f"Original error: {error_msg}"
                ) from e
            raise

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

        Raises:
            FTS5SearchError: If query has invalid FTS5 syntax
        """
        # Sanitize query
        sanitized_query = self.sanitize_query(query)

        sql = text(
            """
            SELECT COUNT(*)
            FROM articles_fts
            WHERE articles_fts MATCH :query
        """
        )

        try:
            result = session.execute(sql, {"query": sanitized_query}).fetchone()
            return result[0] if result else 0
        except OperationalError as e:
            error_msg = str(e)
            if "fts5: syntax error" in error_msg:
                raise FTS5SearchError(
                    f"Invalid FTS5 query syntax: '{query}'\n"
                    f"See 'pydigestor search --help' for query syntax examples."
                ) from e
            raise
