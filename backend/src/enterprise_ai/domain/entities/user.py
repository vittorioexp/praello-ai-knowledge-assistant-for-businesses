"""User domain entity."""

from uuid import UUID

from pydantic import EmailStr, Field

from enterprise_ai.domain.entities.base import Entity
from enterprise_ai.domain.value_objects.role import Role


class User(Entity):
    """Authenticated user within the organization."""

    email: EmailStr
    hashed_password: str
    full_name: str
    role: Role = Role.VIEWER
    is_active: bool = True
    organization_id: UUID | None = None

    def has_permission(self, permission: str) -> bool:
        """Check whether the user's role grants a permission."""
        return self.role.has_permission(permission)

    def can_manage_users(self) -> bool:
        return self.has_permission("users:manage")

    def can_upload_documents(self) -> bool:
        return self.has_permission("documents:upload")

    def can_query_knowledge(self) -> bool:
        return self.has_permission("knowledge:query")

    def can_administer(self) -> bool:
        return self.has_permission("admin:all")
