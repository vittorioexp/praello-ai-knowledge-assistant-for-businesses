"""Document ingestion pipeline — parse, chunk, embed, store."""

from enterprise_ai.ai.ingestion.chunking import ChunkingService
from enterprise_ai.ai.ingestion.parsers import ParserFactory
from enterprise_ai.domain.exceptions import EntityNotFoundError
from enterprise_ai.domain.repositories.document_repository import DocumentRepository
from enterprise_ai.domain.repositories.embedding_service import EmbeddingService
from enterprise_ai.domain.repositories.vector_store import VectorStore
from enterprise_ai.domain.repositories.object_storage import ObjectStorage
from enterprise_ai.infrastructure.storage.remote_materializer import materialize_stream
from enterprise_ai.infrastructure.logging.setup import get_logger

logger = get_logger(__name__)


class IngestionService:
    """Orchestrates the document ingestion pipeline."""

    def __init__(
        self,
        document_repository: DocumentRepository,
        embedding_service: EmbeddingService,
        vector_store: VectorStore,
        chunking_service: ChunkingService,
        object_storage: ObjectStorage | None = None,
    ) -> None:
        self._documents = document_repository
        self._embeddings = embedding_service
        self._vector_store = vector_store
        self._chunking = chunking_service
        self._object_storage = object_storage
        self._batch_size = 128

    async def ingest(self, document_id) -> None:
        """Run full ingestion pipeline for a document."""
        from uuid import UUID

        doc_id = document_id if isinstance(document_id, UUID) else UUID(str(document_id))
        document = await self._documents.get_by_id(doc_id)
        if not document:
            raise EntityNotFoundError(f"Document {doc_id} not found")

        document.mark_processing()
        await self._documents.update(document)

        try:
            parser = ParserFactory.get_parser(document.document_type)
            if self._object_storage is None:
                text = parser.parse(document.file_path)
            else:
                suffix = f".{document.filename.rsplit('.', 1)[-1]}" if "." in document.filename else ""
                async with materialize_stream(
                    self._object_storage.open(document.file_path),
                    suffix=suffix,
                ) as materialized_path:
                    text = parser.parse(str(materialized_path))

            chunks = self._chunking.chunk_text(
                document_id=document.id,
                text=text,
                metadata={
                    "original_filename": document.original_filename,
                    "document_type": document.document_type.value,
                },
            )
            if not chunks:
                document.mark_failed("No chunks produced from document")
                await self._documents.update(document)
                return

            await self._vector_store.ensure_collection(self._embeddings.vector_size)
            await self._vector_store.delete_by_document_id(document.id)

            document_metadata = {
                "tags": document.tags,
                "organization_id": str(document.organization_id)
                if document.organization_id
                else None,
                "document_type": document.document_type.value,
                "original_filename": document.original_filename,
                "allowed_principals": document.allowed_principals,
                "acl_enforced": bool(document.allowed_principals),
            }
            for start in range(0, len(chunks), self._batch_size):
                chunk_batch = chunks[start : start + self._batch_size]
                embeddings = await self._embeddings.embed_texts(
                    [chunk.content for chunk in chunk_batch]
                )
                await self._vector_store.upsert_chunks(
                    chunk_batch,
                    embeddings,
                    document_metadata=document_metadata,
                )

            document.mark_indexed(len(chunks))
            await self._documents.update(document)
            logger.info(
                "document_ingested",
                document_id=str(document.id),
                chunks=len(chunks),
            )
        except Exception as exc:
            logger.exception("ingestion_failed", document_id=str(document.id), error=str(exc))
            document.mark_failed(str(exc))
            await self._documents.update(document)
