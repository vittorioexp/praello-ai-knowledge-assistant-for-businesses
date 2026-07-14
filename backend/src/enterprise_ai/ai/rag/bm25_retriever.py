"""BM25 sparse retrieval."""

import re
from uuid import UUID

from rank_bm25 import BM25Okapi

from enterprise_ai.domain.entities.retrieved_chunk import RetrievedChunk


def _tokenize(text: str) -> list[str]:
    return re.findall(r"\w+", text.lower())


class BM25Retriever:
    """Keyword-based BM25 retrieval over a document corpus."""

    def retrieve(
        self,
        query: str,
        corpus: list[dict],
        *,
        top_k: int = 10,
    ) -> list[RetrievedChunk]:
        """Score corpus chunks against query using BM25."""
        if not corpus:
            return []

        tokenized_corpus = [_tokenize(item["payload"].get("content", "")) for item in corpus]
        if not any(tokenized_corpus):
            return []

        bm25 = BM25Okapi(tokenized_corpus)
        query_tokens = _tokenize(query)
        if not query_tokens:
            return []

        scores = bm25.get_scores(query_tokens)
        ranked_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)

        results: list[RetrievedChunk] = []
        for idx in ranked_indices[:top_k]:
            item = corpus[idx]
            payload = item["payload"]
            results.append(
                RetrievedChunk(
                    id=item["id"],
                    document_id=UUID(payload["document_id"]),
                    content=payload.get("content", ""),
                    chunk_index=payload.get("chunk_index", 0),
                    sparse_score=float(scores[idx]),
                    metadata={
                        k: v
                        for k, v in payload.items()
                        if k not in ("content", "document_id", "chunk_index")
                    },
                )
            )
        return results
