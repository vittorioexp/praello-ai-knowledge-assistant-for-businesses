"""Document ingestion pipeline — parse, chunk, embed, store."""

from enterprise_ai.ai.ingestion.chunking import ChunkingService
from enterprise_ai.ai.ingestion.parsers import ParserFactory
from enterprise_ai.domain.exceptions import EntityNotFoundError
from enterprise_ai.domain.repositories.document_repository import DocumentRepository
from enterprise_ai.domain.repositories.embedding_service import EmbeddingService
from enterprise_ai.domain.repositories.vector_store import VectorStore
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
    ) -> None:
        self._documents = document_repository
        self._embeddings = embedding_service
        self._vector_store = vector_store
        self._chunking = chunking_service

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
            text = parser.parse(document.file_path)

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

            texts = [c.content for c in chunks]
            embeddings = await self._embeddings.embed_texts(texts)

            await self._vector_store.upsert_chunks(
                chunks,
                embeddings,
                document_metadata={
                    "tags": document.tags,
                    "organization_id": str(document.organization_id)
                    if document.organization_id
                    else None,
                    "document_type": document.document_type.value,
                    "original_filename": document.original_filename,
                },
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
