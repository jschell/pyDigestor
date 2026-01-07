"""TF-IDF based ranked search for articles."""

import pickle
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sqlmodel import Session, select

from pydigestor.models import Article


@dataclass
class TfidfResult:
    """TF-IDF search result."""

    article_id: str
    title: str
    summary: str
    score: float  # Cosine similarity score (0-1, higher = more relevant)


class TfidfSearch:
    """
    TF-IDF based ranked search.

    Learns vocabulary from your article corpus and provides transparent,
    ranked search results based on term frequencies and importance.

    Features:
    - Domain-adaptive: learns from your security articles
    - Transparent: can inspect why articles matched
    - Lightweight: no model weights, pure mathematics
    - Temporal tracking: refit periodically to track vocabulary changes
    """

    def __init__(self, index_path: Optional[Path] = None):
        """
        Initialize TF-IDF search.

        Args:
            index_path: Path to saved index (vectorizer + document vectors).
                       Defaults to data/tfidf_index.pkl
        """
        self.index_path = index_path or Path("data/tfidf_index.pkl")
        self.vectorizer: Optional[TfidfVectorizer] = None
        self.doc_vectors = None
        self.article_ids: list[str] = []

        # Load existing index if available
        if self.index_path.exists():
            self.load_index()

    def build_index(self, session: Session, min_df: int = 2, max_features: int = 5000) -> dict:
        """
        Build TF-IDF index from all articles in database.

        Args:
            session: Database session
            min_df: Minimum document frequency (ignore terms appearing in < min_df docs)
            max_features: Maximum number of features (vocabulary size)

        Returns:
            Dictionary with indexing statistics

        Example:
            >>> searcher = TfidfSearch()
            >>> stats = searcher.build_index(session)
            >>> print(f"Indexed {stats['num_articles']} articles")
        """
        # Fetch all articles with content
        articles = session.exec(
            select(Article)
            .where(Article.content.is_not(None))
            .where(Article.content != "")
        ).all()

        if not articles:
            return {
                "num_articles": 0,
                "vocabulary_size": 0,
                "error": "No articles with content found"
            }

        # Prepare documents: combine title + summary + content
        documents = []
        self.article_ids = []

        for article in articles:
            # Combine fields with weights (title appears 3x for importance)
            text_parts = [
                article.title or "",
                article.title or "",  # Title weight
                article.title or "",  # Title weight
                article.summary or "",
                article.content or "",
            ]
            documents.append(" ".join(text_parts))
            self.article_ids.append(article.id)

        # Create TF-IDF vectorizer
        # - Use 1-3 word phrases (ngrams) to capture "SQL injection", "zero day"
        # - Lowercase for normalization
        # - Remove very common (max_df=0.8) and very rare (min_df) terms
        self.vectorizer = TfidfVectorizer(
            max_features=max_features,
            min_df=min_df,
            max_df=0.8,
            ngram_range=(1, 3),
            lowercase=True,
            stop_words='english',
            sublinear_tf=True,  # Use log scaling for term frequency
        )

        # Fit and transform documents
        self.doc_vectors = self.vectorizer.fit_transform(documents)

        # Save index
        self.save_index()

        return {
            "num_articles": len(articles),
            "vocabulary_size": len(self.vectorizer.vocabulary_),
            "max_features": max_features,
            "min_df": min_df,
        }

    def search(
        self,
        session: Session,
        query: str,
        limit: int = 10,
        min_score: float = 0.0
    ) -> list[TfidfResult]:
        """
        Search articles using TF-IDF ranking.

        Args:
            session: Database session
            query: Search query
            limit: Maximum number of results
            min_score: Minimum similarity score (0-1)

        Returns:
            List of ranked results sorted by relevance

        Raises:
            ValueError: If index not built yet

        Example:
            >>> searcher = TfidfSearch()
            >>> results = searcher.search(session, "SQL injection attacks", limit=5)
            >>> for result in results:
            ...     print(f"{result.title}: {result.score:.3f}")
        """
        if self.vectorizer is None or self.doc_vectors is None:
            raise ValueError(
                "TF-IDF index not built. Run 'pydigestor build-tfidf-index' first."
            )

        # Transform query to TF-IDF vector
        query_vector = self.vectorizer.transform([query])

        # Calculate cosine similarity with all documents
        similarities = cosine_similarity(query_vector, self.doc_vectors)[0]

        # Get top results
        top_indices = similarities.argsort()[::-1][:limit]

        # Filter by minimum score and fetch article details
        results = []
        for idx in top_indices:
            score = similarities[idx]
            if score < min_score:
                continue

            article_id = self.article_ids[idx]
            article = session.get(Article, article_id)

            if article:
                results.append(TfidfResult(
                    article_id=article.id,
                    title=article.title or "",
                    summary=article.summary or "",
                    score=float(score),
                ))

        return results

    def get_top_terms(self, n: int = 20) -> list[tuple[str, float]]:
        """
        Get top N terms by average TF-IDF score across all documents.

        Useful for understanding what vocabulary is important in your corpus.

        Args:
            n: Number of top terms to return

        Returns:
            List of (term, average_score) tuples

        Example:
            >>> searcher = TfidfSearch()
            >>> top_terms = searcher.get_top_terms(10)
            >>> for term, score in top_terms:
            ...     print(f"{term}: {score:.3f}")
        """
        if self.vectorizer is None or self.doc_vectors is None:
            raise ValueError("TF-IDF index not built yet")

        # Calculate average TF-IDF score for each term
        avg_scores = self.doc_vectors.mean(axis=0).A1

        # Get feature names
        feature_names = self.vectorizer.get_feature_names_out()

        # Sort by score
        top_indices = avg_scores.argsort()[::-1][:n]

        return [(feature_names[idx], avg_scores[idx]) for idx in top_indices]

    def explain_match(self, query: str, article_id: str) -> dict:
        """
        Explain why a query matched an article.

        Shows which terms contributed most to the similarity score.

        Args:
            query: Search query
            article_id: Article ID to explain

        Returns:
            Dictionary with explanation details

        Example:
            >>> explanation = searcher.explain_match("SQL injection", "article-123")
            >>> print(explanation['matching_terms'])
        """
        if self.vectorizer is None or self.doc_vectors is None:
            raise ValueError("TF-IDF index not built yet")

        # Find article index
        try:
            doc_idx = self.article_ids.index(article_id)
        except ValueError:
            return {"error": f"Article {article_id} not in index"}

        # Get query and document vectors
        query_vector = self.vectorizer.transform([query]).toarray()[0]
        doc_vector = self.doc_vectors[doc_idx].toarray()[0]

        # Find terms present in both
        feature_names = self.vectorizer.get_feature_names_out()
        matching_terms = []

        for idx, (q_val, d_val) in enumerate(zip(query_vector, doc_vector)):
            if q_val > 0 and d_val > 0:
                matching_terms.append({
                    "term": feature_names[idx],
                    "query_weight": float(q_val),
                    "doc_weight": float(d_val),
                    "contribution": float(q_val * d_val),
                })

        # Sort by contribution
        matching_terms.sort(key=lambda x: x["contribution"], reverse=True)

        return {
            "article_id": article_id,
            "query": query,
            "matching_terms": matching_terms,
            "total_score": float(cosine_similarity(
                query_vector.reshape(1, -1),
                doc_vector.reshape(1, -1)
            )[0, 0]),
        }

    def save_index(self) -> None:
        """Save vectorizer and document vectors to disk."""
        self.index_path.parent.mkdir(parents=True, exist_ok=True)

        with open(self.index_path, "wb") as f:
            pickle.dump({
                "vectorizer": self.vectorizer,
                "doc_vectors": self.doc_vectors,
                "article_ids": self.article_ids,
            }, f)

    def load_index(self) -> None:
        """Load vectorizer and document vectors from disk."""
        if not self.index_path.exists():
            return

        with open(self.index_path, "rb") as f:
            data = pickle.load(f)
            self.vectorizer = data["vectorizer"]
            self.doc_vectors = data["doc_vectors"]
            self.article_ids = data["article_ids"]
