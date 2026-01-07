"""Vector similarity search using sqlite-vec."""

from dataclasses import dataclass

from sqlalchemy import text
from sqlmodel import Session

from pydigestor.search.embeddings import EmbeddingGenerator


@dataclass
class SimilarArticle:
    """Similar article result from vector search."""

    article_id: str
    title: str
    summary: str
    distance: float  # cosine distance (lower = more similar)


class VectorSearch:
    """Semantic search using sqlite-vec vector embeddings."""

    def __init__(self):
        """Initialize vector search with embedding generator."""
        self.embedder = EmbeddingGenerator()

    def find_similar(
        self, session: Session, article_id: str, limit: int = 10
    ) -> list[SimilarArticle]:
        """
        Find similar articles using vector similarity.

        Args:
            session: Database session
            article_id: Source article ID to find similar articles to
            limit: Maximum number of results

        Returns:
            List of similar articles sorted by distance (ascending)

        Raises:
            ValueError: If article_id has no embedding

        Example:
            >>> searcher = VectorSearch()
            >>> similar = searcher.find_similar(session, "article-123", limit=5)
            >>> for article in similar:
            ...     print(f"{article.title}: {article.distance:.3f}")
        """
        # Get source article embedding
        sql = text("SELECT embedding FROM article_embeddings WHERE article_id = :id")
        result = session.execute(sql, {"id": article_id}).fetchone()

        if not result:
            raise ValueError(f"No embedding found for article {article_id}")

        source_embedding = result[0]

        # Find similar articles using cosine distance
        sql = text(
            """
            SELECT
                e.article_id,
                a.title,
                a.summary,
                vec_distance_cosine(e.embedding, :source_embedding) as distance
            FROM article_embeddings e
            JOIN articles a ON a.id = e.article_id
            WHERE e.article_id != :source_id
            ORDER BY distance ASC
            LIMIT :limit
        """
        )

        results = session.execute(
            sql,
            {
                "source_embedding": source_embedding,
                "source_id": article_id,
                "limit": limit,
            },
        ).fetchall()

        return [
            SimilarArticle(
                article_id=row[0],
                title=row[1],
                summary=row[2] or "",
                distance=row[3],
            )
            for row in results
        ]

    def search_by_text(
        self, session: Session, query: str, limit: int = 10
    ) -> list[SimilarArticle]:
        """
        Search articles by text query using semantic similarity.

        Args:
            session: Database session
            query: Text query to search for
            limit: Maximum number of results

        Returns:
            List of similar articles sorted by distance (ascending)

        Example:
            >>> searcher = VectorSearch()
            >>> results = searcher.search_by_text(session, "SQL injection attacks", limit=5)
            >>> for article in results:
            ...     print(f"{article.title}: {article.distance:.3f}")
        """
        # Generate embedding for query
        query_embedding = self.embedder.generate(query)

        # Find similar articles
        sql = text(
            """
            SELECT
                e.article_id,
                a.title,
                a.summary,
                vec_distance_cosine(e.embedding, :query_embedding) as distance
            FROM article_embeddings e
            JOIN articles a ON a.id = e.article_id
            ORDER BY distance ASC
            LIMIT :limit
        """
        )

        results = session.execute(
            sql, {"query_embedding": query_embedding, "limit": limit}
        ).fetchall()

        return [
            SimilarArticle(
                article_id=row[0],
                title=row[1],
                summary=row[2] or "",
                distance=row[3],
            )
            for row in results
        ]
