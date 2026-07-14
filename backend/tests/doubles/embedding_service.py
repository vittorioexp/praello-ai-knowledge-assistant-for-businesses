"""Re-export test doubles from production implementations."""

from enterprise_ai.ai.embeddings.mock_embeddings import MockEmbeddingService

__all__ = ["MockEmbeddingService"]
