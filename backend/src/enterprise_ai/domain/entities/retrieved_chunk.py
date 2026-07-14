"""Retrieved chunk domain model."""

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class RetrievedChunk(BaseModel):
    """A chunk returned from retrieval with scoring metadata."""

    id: str
    document_id: UUID
    content: str
    chunk_index: int
    dense_score: float = 0.0
    sparse_score: float = 0.0
    hybrid_score: float = 0.0
    rerank_score: float = 0.0
    metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def document_name(self) -> str:
        return self.metadata.get("original_filename", "unknown")
