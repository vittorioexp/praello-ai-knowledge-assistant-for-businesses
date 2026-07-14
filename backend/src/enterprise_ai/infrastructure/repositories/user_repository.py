"""SQLAlchemy user repository implementation."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from enterprise_ai.domain.entities.user import User
from enterprise_ai.domain.repositories.user_repository import UserRepository
from enterprise_ai.infrastructure.database.mappers.user_mapper import (
    user_entity_to_model,
    user_model_to_entity,
)
from enterprise_ai.infrastructure.database.models.user import UserModel


class SQLAlchemyUserRepository(UserRepository):
    """PostgreSQL-backed user repository."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, user_id: UUID) -> User | None:
        result = await self._session.execute(select(UserModel).where(UserModel.id == user_id))
        model = result.scalar_one_or_none()
        return user_model_to_entity(model) if model else None

    async def get_by_email(self, email: str) -> User | None:
        result = await self._session.execute(select(UserModel).where(UserModel.email == email))
        model = result.scalar_one_or_none()
        return user_model_to_entity(model) if model else None

    async def create(self, user: User) -> User:
        model = user_entity_to_model(user)
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return user_model_to_entity(model)

    async def update(self, user: User) -> User:
        result = await self._session.execute(select(UserModel).where(UserModel.id == user.id))
        model = result.scalar_one_or_none()
        if model is None:
            msg = f"User {user.id} not found"
            raise ValueError(msg)
        model.email = user.email
        model.hashed_password = user.hashed_password
        model.full_name = user.full_name
        model.role = user.role.value
        model.is_active = user.is_active
        model.organization_id = user.organization_id
        model.updated_at = user.updated_at
        await self._session.flush()
        await self._session.refresh(model)
        return user_model_to_entity(model)

    async def list_all(self, *, skip: int = 0, limit: int = 100) -> list[User]:
        result = await self._session.execute(select(UserModel).offset(skip).limit(limit))
        return [user_model_to_entity(m) for m in result.scalars().all()]
