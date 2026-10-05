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
    async def get_by_id(
        self, document_id: UUID, *, organization_id: UUID | None = None
    ) -> Document | None:
        ...

    @abstractmethod
    async def get_by_source(self, source_id: str, source_item_id: str) -> Document | None:
        ...

    @abstractmethod
    async def delete_by_source(self, source_id: str, source_item_id: str) -> UUID | None:
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
        organization_id: UUID | None = None,
        status: str | None = None,
        tags: list[str] | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> list[Document]:
        ...
