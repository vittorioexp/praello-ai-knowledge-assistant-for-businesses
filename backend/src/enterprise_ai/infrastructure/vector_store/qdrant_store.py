"""Qdrant vector store implementation."""

from typing import Any
from uuid import UUID

from qdrant_client import AsyncQdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchAny,
    MatchValue,
    PointStruct,
    VectorParams,
)

from enterprise_ai.domain.entities.document_chunk import DocumentChunk
from enterprise_ai.domain.repositories.vector_store import VectorStore
from enterprise_ai.infrastructure.config.settings import Settings
from enterprise_ai.infrastructure.logging.setup import get_logger

logger = get_logger(__name__)


class QdrantVectorStore(VectorStore):
    """Qdrant-backed vector storage."""

    def __init__(self, settings: Settings) -> None:
        self._client = AsyncQdrantClient(
            host=settings.qdrant_host,
            port=settings.qdrant_port,
        )
        self._collection = settings.qdrant_collection

    async def ensure_collection(self, vector_size: int) -> None:
        exists = await self._client.collection_exists(self._collection)
        if not exists:
            await self._client.create_collection(
                collection_name=self._collection,
                vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
            )
            logger.info("qdrant_collection_created", collection=self._collection)

    async def upsert_chunks(
        self,
        chunks: list[DocumentChunk],
        embeddings: list[list[float]],
        *,
        document_metadata: dict[str, Any],
    ) -> int:
        if len(chunks) != len(embeddings):
            msg = "Chunks and embeddings count mismatch"
            raise ValueError(msg)

        points = [
            PointStruct(
                id=str(chunk.id),
                vector=embedding,
                payload={
                    "document_id": str(chunk.document_id),
                    "chunk_index": chunk.chunk_index,
                    "content": chunk.content,
                    "tags": document_metadata.get("tags", []),
                    "organization_id": document_metadata.get("organization_id"),
                    "document_type": document_metadata.get("document_type"),
                    "original_filename": document_metadata.get("original_filename"),
                    **chunk.metadata,
                },
            )
            for chunk, embedding in zip(chunks, embeddings, strict=True)
        ]

        await self._client.upsert(collection_name=self._collection, points=points)
        logger.info("qdrant_upsert", document_id=str(chunks[0].document_id), count=len(points))
        return len(points)

    async def delete_by_document_id(self, document_id: UUID) -> None:
        await self._client.delete(
            collection_name=self._collection,
            points_selector=Filter(
                must=[
                    FieldCondition(
                        key="document_id",
                        match=MatchValue(value=str(document_id)),
                    )
                ]
            ),
        )
        logger.info("qdrant_deleted", document_id=str(document_id))

    async def search(
        self,
        query_vector: list[float],
        *,
        limit: int = 10,
        filters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        qdrant_filter = self._build_filter(filters) if filters else None
        results = await self._client.search(
            collection_name=self._collection,
            query_vector=query_vector,
            limit=limit,
            query_filter=qdrant_filter,
        )
        return [
            {
                "id": str(hit.id),
                "score": hit.score,
                "payload": hit.payload or {},
            }
            for hit in results
        ]

    async def scroll_chunks(
        self,
        *,
        filters: dict[str, Any] | None = None,
        limit: int = 1000,
    ) -> list[dict[str, Any]]:
        qdrant_filter = self._build_filter(filters) if filters else None
        results: list[dict[str, Any]] = []
        offset = None

        while len(results) < limit:
            batch_limit = min(100, limit - len(results))
            records, offset = await self._client.scroll(
                collection_name=self._collection,
                scroll_filter=qdrant_filter,
                limit=batch_limit,
                offset=offset,
                with_payload=True,
                with_vectors=False,
            )
            if not records:
                break
            for record in records:
                results.append(
                    {
                        "id": str(record.id),
                        "payload": record.payload or {},
                    }
                )
            if offset is None:
                break

        return results[:limit]

    @staticmethod
    def _build_filter(filters: dict[str, Any]) -> Filter:
        conditions = []
        if document_id := filters.get("document_id"):
            conditions.append(
                FieldCondition(key="document_id", match=MatchValue(value=str(document_id)))
            )
        if organization_id := filters.get("organization_id"):
            conditions.append(
                FieldCondition(
                    key="organization_id", match=MatchValue(value=str(organization_id))
                )
            )
        if document_type := filters.get("document_type"):
            conditions.append(
                FieldCondition(key="document_type", match=MatchValue(value=document_type))
            )
        if tags := filters.get("tags"):
            conditions.append(
                FieldCondition(key="tags", match=MatchAny(any=tags))
            )
        return Filter(must=conditions)
