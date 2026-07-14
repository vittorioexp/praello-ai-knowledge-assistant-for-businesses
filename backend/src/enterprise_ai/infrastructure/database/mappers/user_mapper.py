"""ORM to domain entity mappers."""

from enterprise_ai.domain.entities.user import User
from enterprise_ai.domain.value_objects.role import Role
from enterprise_ai.infrastructure.database.models.user import UserModel


def user_model_to_entity(model: UserModel) -> User:
    """Map ORM model to domain entity."""
    return User(
        id=model.id,
        email=model.email,
        hashed_password=model.hashed_password,
        full_name=model.full_name,
        role=Role(model.role),
        is_active=model.is_active,
        organization_id=model.organization_id,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def user_entity_to_model(entity: User) -> UserModel:
    """Map domain entity to ORM model."""
    return UserModel(
        id=entity.id,
        email=entity.email,
        hashed_password=entity.hashed_password,
        full_name=entity.full_name,
        role=entity.role.value,
        is_active=entity.is_active,
        organization_id=entity.organization_id,
        created_at=entity.created_at,
        updated_at=entity.updated_at,
    )
