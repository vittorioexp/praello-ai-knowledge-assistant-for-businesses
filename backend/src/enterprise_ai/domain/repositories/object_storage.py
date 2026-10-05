"""Object storage port for original document bytes."""

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator


class ObjectStorage(ABC):
    """Provider-neutral storage for document content."""

    @abstractmethod
    async def put(self, key: str, content: AsyncIterator[bytes], *, content_type: str) -> int:
        """Store a streamed object and return its size in bytes."""
        ...

    @abstractmethod
    async def open(self, key: str) -> AsyncIterator[bytes]:
        """Stream an object back to a parser or downloader."""
        ...

    @abstractmethod
    async def delete(self, key: str) -> None:
        """Delete an object if it exists."""
        ...
