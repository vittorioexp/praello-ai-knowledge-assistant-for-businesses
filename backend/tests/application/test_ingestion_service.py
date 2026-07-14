"""Tests for ingestion pipeline."""

from uuid import uuid4

import pytest

from enterprise_ai.ai.ingestion.chunking import ChunkingService
from enterprise_ai.application.services.ingestion_service import IngestionService
from enterprise_ai.domain.entities.document import Document
from enterprise_ai.domain.value_objects.document import DocumentStatus, DocumentType
from enterprise_ai.infrastructure.config.settings import Settings
from enterprise_ai.infrastructure.repositories.document_repository import SQLAlchemyDocumentRepository
from enterprise_ai.infrastructure.vector_store.in_memory_store import InMemoryVectorStore
from enterprise_ai.ai.embeddings.mock_embeddings import MockEmbeddingService


@pytest.fixture
def ingestion_service(db_session, test_settings) -> IngestionService:
    return IngestionService(
        SQLAlchemyDocumentRepository(db_session),
        MockEmbeddingService(),
        InMemoryVectorStore(),
        ChunkingService(test_settings),
    )


@pytest.mark.asyncio
async def test_ingest_markdown_document(
    ingestion_service: IngestionService,
    db_session,
    test_settings,
    tmp_path,
) -> None:
    file_path = tmp_path / "handbook.md"
    file_path.write_text(
        "# Employee Handbook\n\n" + "Remote work is allowed. " * 20,
        encoding="utf-8",
    )

    repo = SQLAlchemyDocumentRepository(db_session)
    document = Document(
        filename="handbook.md",
        original_filename="handbook.md",
        content_type="text/markdown",
        document_type=DocumentType.MARKDOWN,
        file_size_bytes=file_path.stat().st_size,
        file_path=str(file_path),
        uploaded_by=uuid4(),
    )
    created = await repo.create(document)

    await ingestion_service.ingest(created.id)

    updated = await repo.get_by_id(created.id)
    assert updated is not None
    assert updated.status == DocumentStatus.INDEXED
    assert updated.chunk_count > 0


@pytest.mark.asyncio
async def test_ingest_missing_document(ingestion_service: IngestionService) -> None:
    from enterprise_ai.domain.exceptions import EntityNotFoundError

    with pytest.raises(EntityNotFoundError):
        await ingestion_service.ingest(uuid4())
