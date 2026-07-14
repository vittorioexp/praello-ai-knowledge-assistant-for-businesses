"""Embedding generation port."""

from abc import ABC, abstractmethod


class EmbeddingService(ABC):
    """Port for text embedding generation."""

    @abstractmethod
    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        ...

    @property
    @abstractmethod
    def vector_size(self) -> int:
        ...
