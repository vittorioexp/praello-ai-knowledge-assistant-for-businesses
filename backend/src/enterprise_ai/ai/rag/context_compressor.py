"""Context compression for LLM prompts."""

from enterprise_ai.domain.entities.retrieved_chunk import RetrievedChunk
from enterprise_ai.infrastructure.config.settings import Settings


class ContextCompressor:
    """Compresses retrieved chunks to fit context window."""

    def __init__(self, settings: Settings) -> None:
        self._max_chars = settings.rag_max_context_chars

    def compress(self, chunks: list[RetrievedChunk]) -> str:
        """Build compressed context string from top chunks."""
        parts: list[str] = []
        total_chars = 0

        for chunk in chunks:
            header = f"[Source: {chunk.document_name}, chunk {chunk.chunk_index}]"
            entry = f"{header}\n{chunk.content}"
            if total_chars + len(entry) > self._max_chars:
                remaining = self._max_chars - total_chars
                if remaining > 100:
                    parts.append(entry[:remaining] + "...")
                break
            parts.append(entry)
            total_chars += len(entry) + 2

        return "\n\n".join(parts)

    def estimate_tokens(self, text: str) -> int:
        """Rough token estimate (chars / 4)."""
        return len(text) // 4
