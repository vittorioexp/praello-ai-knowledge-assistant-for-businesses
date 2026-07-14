"""Document management API routes."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, UploadFile, status

from enterprise_ai.api.dependencies import get_document_service
from enterprise_ai.api.middleware.rbac import require_permission
from enterprise_ai.application.dto.document import (
    DocumentListResponseDTO,
    DocumentResponseDTO,
)
from enterprise_ai.application.services.document_service import DocumentService
from enterprise_ai.domain.entities.user import User
from enterprise_ai.domain.value_objects.role import Permission

router = APIRouter(prefix="/documents", tags=["Knowledge Base"])


@router.post(
    "/upload",
    response_model=DocumentResponseDTO,
    status_code=status.HTTP_201_CREATED,
)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: Annotated[UploadFile, File()],
    document_service: Annotated[DocumentService, Depends(get_document_service)],
    current_user: Annotated[User, Depends(require_permission(Permission.DOCUMENTS_UPLOAD.value))],
    metadata: Annotated[str | None, Form()] = None,
) -> DocumentResponseDTO:
    """Upload a PDF, DOCX, or Markdown document to the knowledge base."""
    content = await file.read()
    upload_meta = DocumentService.parse_upload_metadata(metadata)
    result = await document_service.upload(
        user=current_user,
        filename=file.filename or "unnamed",
        content_type=file.content_type or "application/octet-stream",
        content=content,
        upload_metadata=upload_meta,
    )
    background_tasks.add_task(document_service.process_document, result.id)
    return result


@router.get("", response_model=DocumentListResponseDTO)
async def list_documents(
    document_service: Annotated[DocumentService, Depends(get_document_service)],
    _current_user: Annotated[User, Depends(require_permission(Permission.DOCUMENTS_READ.value))],
    status_filter: str | None = None,
    tags: str | None = None,
    skip: int = 0,
    limit: int = 50,
) -> DocumentListResponseDTO:
    """List knowledge base documents with optional filters."""
    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else None
    return await document_service.list_documents(
        status=status_filter,
        tags=tag_list,
        skip=skip,
        limit=limit,
    )


@router.get("/{document_id}", response_model=DocumentResponseDTO)
async def get_document(
    document_id: UUID,
    document_service: Annotated[DocumentService, Depends(get_document_service)],
    _current_user: Annotated[User, Depends(require_permission(Permission.DOCUMENTS_READ.value))],
) -> DocumentResponseDTO:
    """Get a document by ID."""
    return await document_service.get_by_id(document_id)


@router.post("/{document_id}/reindex", response_model=DocumentResponseDTO)
async def reindex_document(
    document_id: UUID,
    background_tasks: BackgroundTasks,
    document_service: Annotated[DocumentService, Depends(get_document_service)],
    _current_user: Annotated[User, Depends(require_permission(Permission.KNOWLEDGE_ADMIN.value))],
) -> DocumentResponseDTO:
    """Re-process and re-index a document."""
    background_tasks.add_task(document_service.process_document, document_id)
    return await document_service.get_by_id(document_id)


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: UUID,
    document_service: Annotated[DocumentService, Depends(get_document_service)],
    _current_user: Annotated[User, Depends(require_permission(Permission.DOCUMENTS_DELETE.value))],
) -> None:
    """Delete a document and its vector embeddings."""
    await document_service.delete(document_id)
