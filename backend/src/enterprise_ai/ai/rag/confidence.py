"""Confidence scoring for RAG responses."""

from enterprise_ai.domain.entities.retrieved_chunk import RetrievedChunk
from enterprise_ai.infrastructure.config.settings import Settings


class ConfidenceScorer:
    """Calculates answer confidence from retrieval quality."""

    def __init__(self, settings: Settings) -> None:
        self._threshold = settings.rag_confidence_threshold

    def score(
        self,
        chunks: list[RetrievedChunk],
        answer: str,
    ) -> float:
        """Compute confidence score between 0.0 and 1.0."""
        if not chunks:
            return 0.0

        if "don't have enough information" in answer.lower():
            return 0.1

        top_scores = [c.rerank_score or c.hybrid_score for c in chunks[:3]]
        avg_score = sum(top_scores) / len(top_scores)
        confidence = min(1.0, max(0.0, avg_score))

        if confidence < self._threshold:
            confidence *= 0.5

        return round(confidence, 3)
