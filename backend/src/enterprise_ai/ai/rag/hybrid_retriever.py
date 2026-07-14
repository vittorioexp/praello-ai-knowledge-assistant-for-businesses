"""Hybrid dense + sparse retrieval."""

from typing import Any
from uuid import UUID

from enterprise_ai.ai.rag.bm25_retriever import BM25Retriever
from enterprise_ai.ai.rag.fusion import reciprocal_rank_fusion
from enterprise_ai.domain.entities.retrieved_chunk import RetrievedChunk
from enterprise_ai.domain.repositories.embedding_service import EmbeddingService
from enterprise_ai.domain.repositories.vector_store import VectorStore
from enterprise_ai.infrastructure.config.settings import Settings
from enterprise_ai.infrastructure.logging.setup import get_logger

logger = get_logger(__name__)


class HybridRetriever:
    """Combines dense vector search with BM25 sparse retrieval."""

    def __init__(
        self,
        vector_store: VectorStore,
        embedding_service: EmbeddingService,
        settings: Settings,
    ) -> None:
        self._vector_store = vector_store
        self._embeddings = embedding_service
        self._settings = settings
        self._bm25 = BM25Retriever()

    async def retrieve(
        self,
        query: str,
        *,
        filters: dict[str, Any] | None = None,
        top_k: int | None = None,
    ) -> list[RetrievedChunk]:
        """Run hybrid retrieval with RRF fusion."""
        limit = top_k or self._settings.rag_top_k

        query_embedding = (await self._embeddings.embed_texts([query]))[0]
        dense_results = await self._vector_store.search(
            query_embedding,
            limit=limit,
            filters=filters,
        )
        dense_chunks = [
            RetrievedChunk(
                id=r["id"],
                document_id=UUID(r["payload"]["document_id"]),
                content=r["payload"].get("content", ""),
                chunk_index=r["payload"].get("chunk_index", 0),
                dense_score=r.get("score", 0.0),
                metadata={
                    k: v
                    for k, v in r["payload"].items()
                    if k not in ("content", "document_id", "chunk_index")
                },
            )
            for r in dense_results
        ]

        corpus = await self._vector_store.scroll_chunks(filters=filters, limit=2000)
        sparse_chunks = self._bm25.retrieve(query, corpus, top_k=limit)

        if not dense_chunks and not sparse_chunks:
            return []

        if not sparse_chunks:
            for chunk in dense_chunks:
                chunk.hybrid_score = chunk.dense_score
            return dense_chunks[:limit]

        if not dense_chunks:
            for chunk in sparse_chunks:
                chunk.hybrid_score = chunk.sparse_score
            return sparse_chunks[:limit]

        fused = reciprocal_rank_fusion(
            [dense_chunks, sparse_chunks],
            k=self._settings.rag_rrf_k,
        )
        logger.info(
            "hybrid_retrieval",
            query_len=len(query),
            dense=len(dense_chunks),
            sparse=len(sparse_chunks),
            fused=len(fused),
        )
        return fused[:limit]
