"""Reranking retrieved chunks."""

import re

from enterprise_ai.domain.entities.retrieved_chunk import RetrievedChunk


def _tokenize(text: str) -> set[str]:
    return set(re.findall(r"\w+", text.lower()))


class RerankerService:
    """Reranks chunks using hybrid scores and lexical overlap."""

    def rerank(
        self,
        query: str,
        chunks: list[RetrievedChunk],
        *,
        top_k: int = 5,
    ) -> list[RetrievedChunk]:
        """Rerank chunks by combined hybrid score and query overlap."""
        if not chunks:
            return []

        query_tokens = _tokenize(query)
        scored: list[tuple[float, RetrievedChunk]] = []

        max_hybrid = max(c.hybrid_score for c in chunks) or 1.0

        for chunk in chunks:
            content_tokens = _tokenize(chunk.content)
            overlap = len(query_tokens & content_tokens) / max(len(query_tokens), 1)
            normalized_hybrid = chunk.hybrid_score / max_hybrid
            rerank_score = 0.6 * normalized_hybrid + 0.4 * overlap
            chunk.rerank_score = rerank_score
            scored.append((rerank_score, chunk))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [chunk for _, chunk in scored[:top_k]]
