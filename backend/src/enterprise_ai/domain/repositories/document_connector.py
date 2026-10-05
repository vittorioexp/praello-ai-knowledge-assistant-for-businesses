"""Contracts for external document sources."""

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class RemoteDocument:
    """Provider-neutral representation of a remote document version."""

    source_id: str
    item_id: str
    name: str
    content_type: str
    version: str
    modified_at: datetime
    content: AsyncIterator[bytes] | None
    permissions: tuple[str, ...] = ()
    deleted: bool = False


class DocumentConnector(ABC):
    """Incremental connector contract for SharePoint, Drive, and future sources."""

    @abstractmethod
    async def list_changes(
        self, cursor: str | None
    ) -> tuple[list[RemoteDocument], str | None]:
        """Return changed documents and the next provider cursor."""
        ...
