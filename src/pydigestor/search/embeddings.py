"""Embedding generation using SentenceTransformers."""

from functools import lru_cache

from sentence_transformers import SentenceTransformer


@lru_cache(maxsize=1)
def get_embedding_model():
    """
    Load SentenceTransformer model (cached).

    Returns:
        SentenceTransformer model instance (all-MiniLM-L6-v2, 384 dimensions)

    Note:
        Model is cached after first load to avoid reloading on subsequent calls.
        First call will download the model (~80MB) if not already cached.
    """
    return SentenceTransformer("all-MiniLM-L6-v2")


class EmbeddingGenerator:
    """Generate embeddings for articles using SentenceTransformers."""

    def __init__(self):
        """Initialize embedding generator with cached model."""
        self.model = get_embedding_model()

    def generate(self, text: str) -> list[float]:
        """
        Generate embedding for text.

        Args:
            text: Input text to embed

        Returns:
            384-dimensional embedding vector

        Example:
            >>> gen = EmbeddingGenerator()
            >>> embedding = gen.generate("SQL injection vulnerability")
            >>> len(embedding)
            384
        """
        embedding = self.model.encode(text, convert_to_numpy=True)
        return embedding.tolist()

    def generate_for_article(self, article) -> list[float]:
        """
        Generate embedding for article using title and summary.

        Args:
            article: Article model instance with title and summary

        Returns:
            384-dimensional embedding vector

        Note:
            Combines title and summary for better semantic representation.
            If summary is None, uses title only.
        """
        # Combine title and summary for better context
        text = f"{article.title}. {article.summary or ''}"
        return self.generate(text)
