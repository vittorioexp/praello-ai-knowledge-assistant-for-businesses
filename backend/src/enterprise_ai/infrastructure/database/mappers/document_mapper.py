"""Document ORM mappers."""

from enterprise_ai.domain.entities.document import Document
from enterprise_ai.domain.value_objects.document import DocumentStatus, DocumentType
from enterprise_ai.infrastructure.database.models.document import DocumentModel


def document_model_to_entity(model: DocumentModel) -> Document:
    return Document(
        id=model.id,
        filename=model.filename,
        original_filename=model.original_filename,
        content_type=model.content_type,
        document_type=DocumentType(model.document_type),
        file_size_bytes=model.file_size_bytes,
        file_path=model.file_path,
        status=DocumentStatus(model.status),
        error_message=model.error_message,
        chunk_count=model.chunk_count,
        metadata=model.metadata_ or {},
        tags=model.tags or [],
        uploaded_by=model.uploaded_by,
        organization_id=model.organization_id,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def document_entity_to_model(entity: Document) -> DocumentModel:
    return DocumentModel(
        id=entity.id,
        filename=entity.filename,
        original_filename=entity.original_filename,
        content_type=entity.content_type,
        document_type=entity.document_type.value,
        file_size_bytes=entity.file_size_bytes,
        file_path=entity.file_path,
        status=entity.status.value,
        error_message=entity.error_message,
        chunk_count=entity.chunk_count,
        metadata_=entity.metadata,
        tags=entity.tags,
        uploaded_by=entity.uploaded_by,
        organization_id=entity.organization_id,
        created_at=entity.created_at,
        updated_at=entity.updated_at,
    )
