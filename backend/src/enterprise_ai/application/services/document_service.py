"""Document management application service."""

import json
from uuid import UUID

from enterprise_ai.application.dto.document import (
    DocumentListResponseDTO,
    DocumentResponseDTO,
    DocumentUploadMetadataDTO,
)
from enterprise_ai.application.services.ingestion_service import IngestionService
from enterprise_ai.domain.entities.document import Document
from enterprise_ai.domain.entities.user import User
from enterprise_ai.domain.exceptions import EntityNotFoundError, ValidationError
from enterprise_ai.domain.repositories.document_repository import DocumentRepository
from enterprise_ai.domain.repositories.vector_store import VectorStore
from enterprise_ai.domain.value_objects.document import DocumentType
from enterprise_ai.infrastructure.storage.file_storage import FileStorageService


class DocumentService:
    """Handles document upload, listing, and lifecycle management."""

    ALLOWED_CONTENT_TYPES = {
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "text/markdown",
        "text/x-markdown",
        "text/plain",
    }

    def __init__(
        self,
        document_repository: DocumentRepository,
        file_storage: FileStorageService,
        ingestion_service: IngestionService,
        vector_store: VectorStore,
    ) -> None:
        self._documents = document_repository
        self._storage = file_storage
        self._ingestion = ingestion_service
        self._vector_store = vector_store

    async def upload(
        self,
        *,
        user: User,
        filename: str,
        content_type: str,
        content: bytes,
        upload_metadata: DocumentUploadMetadataDTO | None = None,
    ) -> DocumentResponseDTO:
        """Upload and persist a new document."""
        meta = upload_metadata or DocumentUploadMetadataDTO()
        doc_type = DocumentType.from_content_type(content_type) or DocumentType.from_extension(
            filename
        )
        if doc_type is None:
            raise ValidationError(
                "Unsupported file type. Allowed: PDF, DOCX, Markdown",
                details={"content_type": content_type, "filename": filename},
            )
        if content_type not in self.ALLOWED_CONTENT_TYPES and doc_type is None:
            raise ValidationError(f"Unsupported content type: {content_type}")

        file_path = await self._storage.save(filename=filename, content=content)

        document = Document(
            filename=filename,
            original_filename=filename,
            content_type=content_type,
            document_type=doc_type,
            file_size_bytes=len(content),
            file_path=file_path,
            metadata=meta.metadata,
            tags=meta.tags,
            uploaded_by=user.id,
            organization_id=user.organization_id,
        )
        created = await self._documents.create(document)
        return self.to_response(created)

    async def process_document(self, document_id: UUID) -> DocumentResponseDTO:
        """Run ingestion pipeline for a document."""
        await self._ingestion.ingest(document_id)
        document = await self._documents.get_by_id(document_id)
        if not document:
            raise EntityNotFoundError(f"Document {document_id} not found")
        return self.to_response(document)

    async def get_by_id(self, document_id: UUID) -> DocumentResponseDTO:
        document = await self._documents.get_by_id(document_id)
        if not document:
            raise EntityNotFoundError(f"Document {document_id} not found")
        return self.to_response(document)

    async def list_documents(
        self,
        *,
        status: str | None = None,
        tags: list[str] | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> DocumentListResponseDTO:
        items = await self._documents.list_all(status=status, tags=tags, skip=skip, limit=limit)
        return DocumentListResponseDTO(
            items=[self.to_response(d) for d in items],
            total=len(items),
            skip=skip,
            limit=limit,
        )

    async def delete(self, document_id: UUID) -> None:
        document = await self._documents.get_by_id(document_id)
        if not document:
            raise EntityNotFoundError(f"Document {document_id} not found")
        await self._vector_store.delete_by_document_id(document_id)
        await self._storage.delete(document.file_path)
        await self._documents.delete(document_id)

    @staticmethod
    def to_response(document: Document) -> DocumentResponseDTO:
        return DocumentResponseDTO(
            id=document.id,
            filename=document.filename,
            original_filename=document.original_filename,
            content_type=document.content_type,
            document_type=document.document_type,
            file_size_bytes=document.file_size_bytes,
            status=document.status,
            error_message=document.error_message,
            chunk_count=document.chunk_count,
            metadata=document.metadata,
            tags=document.tags,
            uploaded_by=document.uploaded_by,
            organization_id=document.organization_id,
            created_at=document.created_at,
            updated_at=document.updated_at,
        )

    @staticmethod
    def parse_upload_metadata(raw: str | None) -> DocumentUploadMetadataDTO:
        """Parse optional JSON metadata from multipart form."""
        if not raw:
            return DocumentUploadMetadataDTO()
        try:
            data = json.loads(raw)
            return DocumentUploadMetadataDTO.model_validate(data)
        except (json.JSONDecodeError, ValueError) as exc:
            raise ValidationError("Invalid metadata JSON") from exc
