"""Vector store port for embedding storage and retrieval."""

from abc import ABC, abstractmethod
from typing import Any
from uuid import UUID

from enterprise_ai.domain.entities.document_chunk import DocumentChunk


class VectorStore(ABC):
    """Port for vector database operations."""

    @abstractmethod
    async def ensure_collection(self, vector_size: int) -> None:
        ...

    @abstractmethod
    async def upsert_chunks(
        self,
        chunks: list[DocumentChunk],
        embeddings: list[list[float]],
        *,
        document_metadata: dict[str, Any],
    ) -> int:
        ...

    @abstractmethod
    async def delete_by_document_id(self, document_id: UUID) -> None:
        ...

    @abstractmethod
    async def search(
        self,
        query_vector: list[float],
        *,
        limit: int = 10,
        filters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        ...

    @abstractmethod
    async def scroll_chunks(
        self,
        *,
        filters: dict[str, Any] | None = None,
        limit: int = 1000,
    ) -> list[dict[str, Any]]:
        """Retrieve chunks for sparse/BM25 retrieval."""
        ...
