"""Tests for text chunking."""

from uuid import uuid4

import pytest

from enterprise_ai.ai.ingestion.chunking import ChunkingService
from enterprise_ai.infrastructure.config.settings import Settings


@pytest.fixture
def chunking_service() -> ChunkingService:
    settings = Settings(
        app_env="test",
        app_secret_key="test-secret-key-minimum-32-chars-long",
        jwt_secret_key="test-jwt-secret-key-min-32-chars",
        chunk_size=100,
        chunk_overlap=20,
    )
    return ChunkingService(settings)


def test_chunk_text_produces_multiple_chunks(chunking_service: ChunkingService) -> None:
    doc_id = uuid4()
    text = " ".join(["word"] * 200)
    chunks = chunking_service.chunk_text(document_id=doc_id, text=text)
    assert len(chunks) > 1
    assert all(c.document_id == doc_id for c in chunks)
    assert chunks[0].chunk_index == 0


def test_chunk_text_preserves_metadata(chunking_service: ChunkingService) -> None:
    doc_id = uuid4()
    chunks = chunking_service.chunk_text(
        document_id=doc_id,
        text="A short document for testing.",
        metadata={"source": "test"},
    )
    assert chunks[0].metadata["source"] == "test"
