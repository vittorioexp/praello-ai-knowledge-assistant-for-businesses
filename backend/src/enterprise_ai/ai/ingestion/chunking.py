"""Text chunking for document ingestion."""

from uuid import UUID

from langchain_text_splitters import RecursiveCharacterTextSplitter

from enterprise_ai.domain.entities.document_chunk import DocumentChunk
from enterprise_ai.infrastructure.config.settings import Settings


class ChunkingService:
    """Splits document text into overlapping chunks."""

    def __init__(self, settings: Settings) -> None:
        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""],
        )

    def chunk_text(
        self,
        *,
        document_id: UUID,
        text: str,
        metadata: dict | None = None,
    ) -> list[DocumentChunk]:
        """Split text into document chunks."""
        base_metadata = metadata or {}
        splits = self._splitter.split_text(text)
        return [
            DocumentChunk(
                document_id=document_id,
                content=chunk,
                chunk_index=index,
                metadata={**base_metadata, "chunk_index": index},
            )
            for index, chunk in enumerate(splits)
            if chunk.strip()
        ]
