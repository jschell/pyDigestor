"""Hybrid search combining FTS5 and vector search using RRF."""

from dataclasses import dataclass

from sqlmodel import Session

from pydigestor.search.fts import FTS5Search
from pydigestor.search.vector import VectorSearch


@dataclass
class HybridResult:
    """Hybrid search result combining FTS5 and vector search."""

    article_id: str
    title: str
    snippet: str
    rrf_score: float
    fts_rank: float | None
    vector_distance: float | None


class HybridSearch:
    """Hybrid search using Reciprocal Rank Fusion (RRF)."""

    def __init__(self, k: int = 60):
        """
        Initialize hybrid search.

        Args:
            k: RRF constant (default 60, recommended by research)

        Note:
            The k parameter controls how much emphasis to place on the top-ranked
            results. Higher k values reduce the impact of rank position.
        """
        self.k = k
        self.fts = FTS5Search()
        self.vector = VectorSearch()

    def search(
        self,
        session: Session,
        query: str,
        limit: int = 10,
        fts_weight: float = 0.5,
        vector_weight: float = 0.5,
    ) -> list[HybridResult]:
        """
        Hybrid search with RRF ranking.

        Args:
            session: Database session
            query: Search query
            limit: Max results to return
            fts_weight: Weight for FTS5 scores (0-1, default 0.5)
            vector_weight: Weight for vector scores (0-1, default 0.5)

        Returns:
            Combined and ranked results

        Example:
            >>> searcher = HybridSearch()
            >>> results = searcher.search(session, "SQL injection", limit=10)
            >>> for r in results:
            ...     print(f"{r.title}: RRF={r.rrf_score:.3f}")

        Note:
            RRF formula: score = weight * (1 / (k + rank))
            Results from both FTS5 and vector search are combined and re-ranked.
        """
        # Get FTS5 results (fetch more for better RRF combination)
        fts_results = self.fts.search(session, query, limit=50)
        fts_ranks = {r.article_id: (i + 1, r) for i, r in enumerate(fts_results)}

        # Get vector results (fetch more for better RRF combination)
        vector_results = self.vector.search_by_text(session, query, limit=50)
        vector_ranks = {r.article_id: (i + 1, r) for i, r in enumerate(vector_results)}

        # Combine with RRF
        all_ids = set(fts_ranks.keys()) | set(vector_ranks.keys())

        scored_results = []
        for article_id in all_ids:
            fts_rank, fts_result = fts_ranks.get(article_id, (None, None))
            vector_rank, vector_result = vector_ranks.get(article_id, (None, None))

            # RRF score: 1/(k + rank)
            fts_score = fts_weight / (self.k + fts_rank) if fts_rank else 0
            vector_score = (
                vector_weight / (self.k + vector_rank) if vector_rank else 0
            )

            rrf_score = fts_score + vector_score

            # Get article details (prefer FTS for snippet)
            if fts_result:
                title = fts_result.title
                snippet = fts_result.snippet
            else:
                title = vector_result.title
                snippet = vector_result.summary[:100] + "..." if vector_result.summary else ""

            scored_results.append(
                HybridResult(
                    article_id=article_id,
                    title=title,
                    snippet=snippet,
                    rrf_score=rrf_score,
                    fts_rank=fts_result.rank if fts_result else None,
                    vector_distance=vector_result.distance if vector_result else None,
                )
            )

        # Sort by RRF score descending (higher is better)
        scored_results.sort(key=lambda x: x.rrf_score, reverse=True)

        return scored_results[:limit]
