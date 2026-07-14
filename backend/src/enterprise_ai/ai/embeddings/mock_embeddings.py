"""Mock embedding service for development and testing."""

from enterprise_ai.domain.repositories.embedding_service import EmbeddingService


class MockEmbeddingService(EmbeddingService):
    """Deterministic fake embeddings without API calls."""

    def __init__(self, vector_size: int = 8) -> None:
        self._vector_size = vector_size

    @property
    def vector_size(self) -> int:
        return self._vector_size

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [
            [
                float((i + j) % self._vector_size) / self._vector_size
                for j in range(self._vector_size)
            ]
            for i, _ in enumerate(texts)
        ]
