"""Document domain entity."""

from typing import Any
from uuid import UUID

from pydantic import Field

from enterprise_ai.domain.entities.base import Entity
from enterprise_ai.domain.value_objects.document import DocumentStatus, DocumentType


class Document(Entity):
    """Uploaded knowledge base document."""

    filename: str
    original_filename: str
    content_type: str
    document_type: DocumentType
    file_size_bytes: int
    file_path: str
    status: DocumentStatus = DocumentStatus.PENDING
    error_message: str | None = None
    chunk_count: int = 0
    metadata: dict[str, Any] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)
    uploaded_by: UUID
    organization_id: UUID | None = None

    def mark_processing(self) -> None:
        self.status = DocumentStatus.PROCESSING
        self.error_message = None
        self.touch()

    def mark_indexed(self, chunk_count: int) -> None:
        self.status = DocumentStatus.INDEXED
        self.chunk_count = chunk_count
        self.error_message = None
        self.touch()

    def mark_failed(self, error: str) -> None:
        self.status = DocumentStatus.FAILED
        self.error_message = error
        self.touch()
