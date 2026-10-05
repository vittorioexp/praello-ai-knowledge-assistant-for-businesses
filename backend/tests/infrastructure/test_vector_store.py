"""Tests for in-memory vector store."""

from uuid import uuid4

import pytest

from enterprise_ai.domain.entities.document_chunk import DocumentChunk
from enterprise_ai.infrastructure.vector_store.in_memory_store import InMemoryVectorStore


@pytest.fixture
def vector_store() -> InMemoryVectorStore:
    return InMemoryVectorStore()


@pytest.mark.asyncio
async def test_upsert_and_search_with_metadata_filter(vector_store: InMemoryVectorStore) -> None:
    doc_id = uuid4()
    chunks = [
        DocumentChunk(document_id=doc_id, content="HR policy text", chunk_index=0),
        DocumentChunk(document_id=doc_id, content="Security policy text", chunk_index=1),
    ]
    embeddings = [[0.1] * 8, [0.2] * 8]

    await vector_store.ensure_collection(8)
    await vector_store.upsert_chunks(
        chunks,
        embeddings,
        document_metadata={
            "tags": ["policy", "hr"],
            "organization_id": "org-123",
            "document_type": "markdown",
            "original_filename": "handbook.md",
        },
    )

    results = await vector_store.search([0.1] * 8, filters={"tags": ["hr"]})
    assert len(results) == 2

    await vector_store.delete_by_document_id(doc_id)
    results_after = await vector_store.search([0.1] * 8)
    assert len(results_after) == 0


@pytest.mark.asyncio
async def test_acl_filter_keeps_legacy_documents_visible(vector_store: InMemoryVectorStore) -> None:
    chunk = DocumentChunk(document_id=uuid4(), content="legacy", chunk_index=0)
    await vector_store.ensure_collection(8)
    await vector_store.upsert_chunks(
        [chunk],
        [[0.1] * 8],
        document_metadata={"acl_enforced": False, "allowed_principals": []},
    )

    results = await vector_store.search([0.1] * 8, filters={"acl_principal": "user@example.com"})

    assert len(results) == 1


@pytest.mark.asyncio
async def test_acl_filter_hides_documents_for_other_users(vector_store: InMemoryVectorStore) -> None:
    chunk = DocumentChunk(document_id=uuid4(), content="confidential", chunk_index=0)
    await vector_store.ensure_collection(8)
    await vector_store.upsert_chunks(
        [chunk],
        [[0.1] * 8],
        document_metadata={
            "acl_enforced": True,
            "allowed_principals": ["allowed@example.com"],
        },
    )

    denied = await vector_store.search(
        [0.1] * 8,
        filters={"acl_principal": "denied@example.com"},
    )
    allowed = await vector_store.search(
        [0.1] * 8,
        filters={"acl_principal": "allowed@example.com"},
    )

    assert denied == []
    assert len(allowed) == 1
