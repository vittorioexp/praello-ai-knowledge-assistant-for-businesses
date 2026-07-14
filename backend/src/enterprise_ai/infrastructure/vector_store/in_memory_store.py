"""In-memory vector store for development and testing."""

from typing import Any
from uuid import UUID

from enterprise_ai.ai.rag.similarity import cosine_similarity
from enterprise_ai.domain.entities.document_chunk import DocumentChunk
from enterprise_ai.domain.repositories.vector_store import VectorStore


class InMemoryVectorStore(VectorStore):
    """In-memory vector storage without external dependencies."""

    def __init__(self) -> None:
        self._points: dict[str, dict[str, Any]] = {}
        self._vector_size: int = 1536

    async def ensure_collection(self, vector_size: int) -> None:
        self._vector_size = vector_size

    async def upsert_chunks(
        self,
        chunks: list[DocumentChunk],
        embeddings: list[list[float]],
        *,
        document_metadata: dict[str, Any],
    ) -> int:
        for chunk, embedding in zip(chunks, embeddings, strict=True):
            self._points[str(chunk.id)] = {
                "vector": embedding,
                "payload": {
                    "document_id": str(chunk.document_id),
                    "chunk_index": chunk.chunk_index,
                    "content": chunk.content,
                    **document_metadata,
                    **chunk.metadata,
                },
            }
        return len(chunks)

    async def delete_by_document_id(self, document_id: UUID) -> None:
        doc_id = str(document_id)
        self._points = {
            k: v
            for k, v in self._points.items()
            if v["payload"].get("document_id") != doc_id
        }

    def _matches_filters(self, payload: dict[str, Any], filters: dict[str, Any] | None) -> bool:
        if not filters:
            return True
        if doc_id := filters.get("document_id"):
            if payload.get("document_id") != str(doc_id):
                return False
        if org_id := filters.get("organization_id"):
            if payload.get("organization_id") != str(org_id):
                return False
        if doc_type := filters.get("document_type"):
            if payload.get("document_type") != doc_type:
                return False
        if tags := filters.get("tags"):
            point_tags = payload.get("tags", [])
            if not any(t in point_tags for t in tags):
                return False
        return True

    async def search(
        self,
        query_vector: list[float],
        *,
        limit: int = 10,
        filters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        scored: list[tuple[float, str, dict[str, Any]]] = []
        for point_id, point in self._points.items():
            payload = point["payload"]
            if not self._matches_filters(payload, filters):
                continue
            score = cosine_similarity(query_vector, point["vector"])
            scored.append((score, point_id, payload))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [
            {"id": point_id, "score": score, "payload": payload}
            for score, point_id, payload in scored[:limit]
        ]

    async def scroll_chunks(
        self,
        *,
        filters: dict[str, Any] | None = None,
        limit: int = 1000,
    ) -> list[dict[str, Any]]:
        results = []
        for point_id, point in self._points.items():
            if self._matches_filters(point["payload"], filters):
                results.append({"id": point_id, "payload": point["payload"]})
            if len(results) >= limit:
                break
        return results
