"""Reciprocal Rank Fusion for hybrid retrieval."""

from enterprise_ai.domain.entities.retrieved_chunk import RetrievedChunk


def reciprocal_rank_fusion(
    ranked_lists: list[list[RetrievedChunk]],
    *,
    k: int = 60,
    id_key: str = "id",
) -> list[RetrievedChunk]:
    """Merge multiple ranked lists using RRF."""
    scores: dict[str, float] = {}
    chunks: dict[str, RetrievedChunk] = {}

    for ranked in ranked_lists:
        for rank, chunk in enumerate(ranked):
            chunk_id = chunk.id
            scores[chunk_id] = scores.get(chunk_id, 0.0) + 1.0 / (k + rank + 1)
            if chunk_id not in chunks:
                chunks[chunk_id] = chunk

    fused = []
    for chunk_id, score in sorted(scores.items(), key=lambda x: x[1], reverse=True):
        chunk = chunks[chunk_id]
        chunk.hybrid_score = score
        fused.append(chunk)
    return fused
