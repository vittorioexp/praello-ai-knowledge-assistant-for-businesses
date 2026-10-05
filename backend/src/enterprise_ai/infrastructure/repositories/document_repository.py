"""SQLAlchemy document repository."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from enterprise_ai.domain.entities.document import Document
from enterprise_ai.domain.repositories.document_repository import DocumentRepository
from enterprise_ai.infrastructure.database.mappers.document_mapper import (
    document_entity_to_model,
    document_model_to_entity,
)
from enterprise_ai.infrastructure.database.models.document import DocumentModel


class SQLAlchemyDocumentRepository(DocumentRepository):
    """PostgreSQL-backed document repository."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, document: Document) -> Document:
        model = document_entity_to_model(document)
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return document_model_to_entity(model)

    async def get_by_id(
        self, document_id: UUID, *, organization_id: UUID | None = None
    ) -> Document | None:
        query = select(DocumentModel).where(DocumentModel.id == document_id)
        if organization_id is not None:
            query = query.where(DocumentModel.organization_id == organization_id)
        result = await self._session.execute(query)
        model = result.scalar_one_or_none()
        return document_model_to_entity(model) if model else None

    async def get_by_source(self, source_id: str, source_item_id: str) -> Document | None:
        result = await self._session.execute(
            select(DocumentModel).where(
                DocumentModel.source_id == source_id,
                DocumentModel.source_item_id == source_item_id,
            )
        )
        model = result.scalar_one_or_none()
        return document_model_to_entity(model) if model else None

    async def delete_by_source(self, source_id: str, source_item_id: str) -> UUID | None:
        result = await self._session.execute(
            select(DocumentModel).where(
                DocumentModel.source_id == source_id,
                DocumentModel.source_item_id == source_item_id,
            )
        )
        model = result.scalar_one_or_none()
        if model is None:
            return None
        document_id = model.id
        await self._session.delete(model)
        await self._session.flush()
        return document_id

    async def update(self, document: Document) -> Document:
        result = await self._session.execute(
            select(DocumentModel).where(DocumentModel.id == document.id)
        )
        model = result.scalar_one_or_none()
        if model is None:
            msg = f"Document {document.id} not found"
            raise ValueError(msg)
        model.filename = document.filename
        model.original_filename = document.original_filename
        model.content_type = document.content_type
        model.document_type = document.document_type.value
        model.file_size_bytes = document.file_size_bytes
        model.file_path = document.file_path
        model.status = document.status.value
        model.error_message = document.error_message
        model.chunk_count = document.chunk_count
        model.metadata_ = document.metadata
        model.tags = document.tags
        model.organization_id = document.organization_id
        model.source_type = document.source_type
        model.source_id = document.source_id
        model.source_item_id = document.source_item_id
        model.source_version = document.source_version
        model.allowed_principals = document.allowed_principals
        model.updated_at = document.updated_at
        await self._session.flush()
        await self._session.refresh(model)
        return document_model_to_entity(model)

    async def delete(self, document_id: UUID) -> bool:
        result = await self._session.execute(
            select(DocumentModel).where(DocumentModel.id == document_id)
        )
        model = result.scalar_one_or_none()
        if model is None:
            return False
        await self._session.delete(model)
        await self._session.flush()
        return True

    async def list_all(
        self,
        *,
        uploaded_by: UUID | None = None,
        organization_id: UUID | None = None,
        status: str | None = None,
        tags: list[str] | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> list[Document]:
        query = select(DocumentModel)
        if uploaded_by:
            query = query.where(DocumentModel.uploaded_by == uploaded_by)
        if organization_id is not None:
            query = query.where(DocumentModel.organization_id == organization_id)
        if status:
            query = query.where(DocumentModel.status == status)
        if tags:
            for tag in tags:
                query = query.where(DocumentModel.tags.contains([tag]))
        query = query.order_by(DocumentModel.created_at.desc()).offset(skip).limit(limit)
        result = await self._session.execute(query)
        return [document_model_to_entity(m) for m in result.scalars().all()]
