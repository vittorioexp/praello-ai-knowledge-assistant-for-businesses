"""Re-export test doubles from production implementations."""

from enterprise_ai.ai.embeddings.mock_embeddings import MockEmbeddingService
from enterprise_ai.infrastructure.vector_store.in_memory_store import InMemoryVectorStore

__all__ = ["InMemoryVectorStore", "MockEmbeddingService"]
