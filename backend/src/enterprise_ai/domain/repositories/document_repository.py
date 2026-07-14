"""Document repository port."""

from abc import ABC, abstractmethod
from uuid import UUID

from enterprise_ai.domain.entities.document import Document


class DocumentRepository(ABC):
    """Port for document persistence."""

    @abstractmethod
    async def create(self, document: Document) -> Document:
        ...

    @abstractmethod
    async def get_by_id(self, document_id: UUID) -> Document | None:
        ...

    @abstractmethod
    async def update(self, document: Document) -> Document:
        ...

    @abstractmethod
    async def delete(self, document_id: UUID) -> bool:
        ...

    @abstractmethod
    async def list_all(
        self,
        *,
        uploaded_by: UUID | None = None,
        status: str | None = None,
        tags: list[str] | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> list[Document]:
        ...
