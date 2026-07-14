"""Repository interfaces (ports)."""

from abc import ABC, abstractmethod
from uuid import UUID

from enterprise_ai.domain.entities.user import User


class UserRepository(ABC):
    """Port for user persistence."""

    @abstractmethod
    async def get_by_id(self, user_id: UUID) -> User | None:
        ...

    @abstractmethod
    async def get_by_email(self, email: str) -> User | None:
        ...

    @abstractmethod
    async def create(self, user: User) -> User:
        ...

    @abstractmethod
    async def update(self, user: User) -> User:
        ...

    @abstractmethod
    async def list_all(self, *, skip: int = 0, limit: int = 100) -> list[User]:
        ...
