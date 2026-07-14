"""Document DTOs."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from enterprise_ai.domain.value_objects.document import DocumentStatus, DocumentType


class DocumentResponseDTO(BaseModel):
    """Public document representation."""

    id: UUID
    filename: str
    original_filename: str
    content_type: str
    document_type: DocumentType
    file_size_bytes: int
    status: DocumentStatus
    error_message: str | None = None
    chunk_count: int
    metadata: dict[str, Any] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)
    uploaded_by: UUID
    organization_id: UUID | None = None
    created_at: datetime
    updated_at: datetime


class DocumentListResponseDTO(BaseModel):
    """Paginated document list."""

    items: list[DocumentResponseDTO]
    total: int
    skip: int
    limit: int


class DocumentUploadMetadataDTO(BaseModel):
    """Optional metadata for document upload."""

    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
