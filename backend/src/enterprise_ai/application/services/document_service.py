"""Document management application service."""

import json
from collections.abc import Awaitable, Callable
from uuid import UUID, uuid4

from enterprise_ai.application.dto.document import (
    DocumentListResponseDTO,
    DocumentResponseDTO,
    DocumentUploadMetadataDTO,
)
from enterprise_ai.application.services.ingestion_service import IngestionService
from enterprise_ai.domain.entities.document import Document
from enterprise_ai.domain.entities.user import User
from enterprise_ai.domain.repositories.document_connector import RemoteDocument
from enterprise_ai.domain.exceptions import EntityNotFoundError, ValidationError
from enterprise_ai.domain.repositories.document_repository import DocumentRepository
from enterprise_ai.domain.repositories.vector_store import VectorStore
from enterprise_ai.domain.repositories.object_storage import ObjectStorage
from enterprise_ai.domain.value_objects.document import DocumentStatus, DocumentType
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
        object_storage: ObjectStorage | None = None,
        max_upload_size_bytes: int | None = None,
    ) -> None:
        self._documents = document_repository
        self._storage = file_storage
        self._ingestion = ingestion_service
        self._vector_store = vector_store
        self._object_storage = object_storage
        self._max_upload_size_bytes = max_upload_size_bytes

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

        if self._object_storage is None:
            file_path = await self._storage.save(filename=filename, content=content)
        else:
            file_path = f"uploads/{uuid4().hex}_{filename}"

            async def content_stream():
                if (
                    self._max_upload_size_bytes is not None
                    and len(content) > self._max_upload_size_bytes
                ):
                    raise ValidationError("File exceeds the configured upload size limit")
                yield content

            await self._object_storage.put(
                file_path,
                content_stream(),
                content_type=content_type,
            )

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

    async def upload_stream(
        self,
        *,
        user: User,
        filename: str,
        content_type: str,
        read_chunk: Callable[[int], Awaitable[bytes]],
        upload_metadata: DocumentUploadMetadataDTO | None = None,
    ) -> DocumentResponseDTO:
        """Upload a document without buffering the complete file in memory."""
        meta = upload_metadata or DocumentUploadMetadataDTO()
        doc_type = DocumentType.from_content_type(content_type) or DocumentType.from_extension(
            filename
        )
        if doc_type is None:
            raise ValidationError("Unsupported file type. Allowed: PDF, DOCX, Markdown")

        if self._object_storage is None:
            file_path, file_size = await self._storage.save_stream(
                filename=filename,
                read_chunk=read_chunk,
            )
        else:
            file_path = f"uploads/{uuid4().hex}_{filename}"

            async def content_stream():
                total_size = 0
                while chunk := await read_chunk(1024 * 1024):
                    total_size += len(chunk)
                    if (
                        self._max_upload_size_bytes is not None
                        and total_size > self._max_upload_size_bytes
                    ):
                        raise ValidationError("File exceeds the configured upload size limit")
                    yield chunk

            file_size = await self._object_storage.put(
                file_path,
                content_stream(),
                content_type=content_type,
            )
        document = Document(
            filename=filename,
            original_filename=filename,
            content_type=content_type,
            document_type=doc_type,
            file_size_bytes=file_size,
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

    async def get_by_id(
        self, document_id: UUID, *, organization_id: UUID | None = None
    ) -> DocumentResponseDTO:
        document = await self._documents.get_by_id(document_id, organization_id=organization_id)
        if not document:
            raise EntityNotFoundError(f"Document {document_id} not found")
        return self.to_response(document)

    async def list_documents(
        self,
        *,
        status: str | None = None,
        tags: list[str] | None = None,
        organization_id: UUID | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> DocumentListResponseDTO:
        items = await self._documents.list_all(
            status=status,
            tags=tags,
            organization_id=organization_id,
            skip=skip,
            limit=limit,
        )
        return DocumentListResponseDTO(
            items=[self.to_response(d) for d in items],
            total=len(items),
            skip=skip,
            limit=limit,
        )

    async def delete(self, document_id: UUID, *, organization_id: UUID | None = None) -> None:
        document = await self._documents.get_by_id(document_id, organization_id=organization_id)
        if not document:
            raise EntityNotFoundError(f"Document {document_id} not found")
        await self._vector_store.delete_by_document_id(document_id)
        if self._object_storage is None:
            await self._storage.delete(document.file_path)
        else:
            await self._object_storage.delete(document.file_path)
        await self._documents.delete(document_id)

    async def delete_by_source(self, source_id: str, source_item_id: str) -> bool:
        """Delete a remotely sourced document and its indexed content."""
        document = await self._documents.get_by_source(source_id, source_item_id)
        if not document:
            return False
        await self._vector_store.delete_by_document_id(document.id)
        if self._object_storage is None:
            await self._storage.delete(document.file_path)
        else:
            await self._object_storage.delete(document.file_path)
        await self._documents.delete_by_source(source_id, source_item_id)
        return True

    async def upsert_remote(
        self,
        *,
        remote: RemoteDocument,
        uploaded_by: UUID,
        organization_id: UUID | None,
    ) -> DocumentResponseDTO:
        """Create or update a document received from an external connector."""
        if remote.content is None:
            raise ValidationError("Remote document has no content")
        document_type = DocumentType.from_content_type(remote.content_type) or DocumentType.from_extension(
            remote.name
        )
        if document_type is None:
            raise ValidationError(f"Unsupported remote file type: {remote.content_type}")
        if self._object_storage is None:
            file_path, file_size = await self._storage.save_iterator(
                filename=remote.name,
                content=remote.content,
            )
        else:
            file_path = f"{remote.source_id}/{remote.item_id}"
            file_size = await self._object_storage.put(
                file_path,
                remote.content,
                content_type=remote.content_type,
            )
        existing = await self._documents.get_by_source(remote.source_id, remote.item_id)
        if existing:
            if self._object_storage is None:
                await self._storage.delete(existing.file_path)
            else:
                await self._object_storage.delete(existing.file_path)
            existing.filename = remote.name
            existing.original_filename = remote.name
            existing.content_type = remote.content_type
            existing.document_type = document_type
            existing.file_size_bytes = file_size
            existing.file_path = file_path
            existing.source_version = remote.version
            existing.allowed_principals = list(remote.permissions)
            existing.status = DocumentStatus.PENDING
            updated = await self._documents.update(existing)
            return self.to_response(updated)
        document = Document(
            filename=remote.name,
            original_filename=remote.name,
            content_type=remote.content_type,
            document_type=document_type,
            file_size_bytes=file_size,
            file_path=file_path,
            uploaded_by=uploaded_by,
            organization_id=organization_id,
            source_type=remote.source_id,
            source_id=remote.source_id,
            source_item_id=remote.item_id,
            source_version=remote.version,
            allowed_principals=list(remote.permissions),
        )
        created = await self._documents.create(document)
        return self.to_response(created)

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
