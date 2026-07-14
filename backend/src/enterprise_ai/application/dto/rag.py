"""RAG query and response DTOs."""

from uuid import UUID

from pydantic import BaseModel, Field


class RAGQueryRequestDTO(BaseModel):
    """Knowledge base query request."""

    query: str = Field(min_length=1, max_length=2000)
    tags: list[str] | None = None
    document_id: UUID | None = None
    use_multi_query: bool = True
    use_reranking: bool = True
    top_k: int | None = Field(default=None, ge=1, le=50)


class SourceCitationDTO(BaseModel):
    """Source citation for a RAG answer."""

    document_id: UUID
    document_name: str
    chunk_index: int
    excerpt: str
    relevance_score: float


class RAGQueryResponseDTO(BaseModel):
    """RAG query response with answer, confidence, and citations."""

    answer: str
    confidence: float = Field(ge=0.0, le=1.0)
    sources: list[SourceCitationDTO]
    rewritten_queries: list[str] = Field(default_factory=list)
    retrieval_count: int
    context_tokens_estimate: int
