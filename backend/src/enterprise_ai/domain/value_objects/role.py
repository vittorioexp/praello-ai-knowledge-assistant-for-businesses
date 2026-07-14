"""Role-based access control value objects."""

from enum import Enum


class Permission(str, Enum):
    """Granular permissions for RBAC."""

    USERS_READ = "users:read"
    USERS_MANAGE = "users:manage"
    DOCUMENTS_READ = "documents:read"
    DOCUMENTS_UPLOAD = "documents:upload"
    DOCUMENTS_DELETE = "documents:delete"
    KNOWLEDGE_QUERY = "knowledge:query"
    KNOWLEDGE_ADMIN = "knowledge:admin"
    AGENT_EXECUTE = "agent:execute"
    AGENT_APPROVE = "agent:approve"
    ADMIN_ALL = "admin:all"


class Role(str, Enum):
    """Organizational roles with hierarchical permissions."""

    VIEWER = "viewer"
    CONTRIBUTOR = "contributor"
    ANALYST = "analyst"
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"

    @property
    def permissions(self) -> frozenset[Permission]:
        """Return permissions granted to this role."""
        mapping: dict[Role, frozenset[Permission]] = {
            Role.VIEWER: frozenset(
                {
                    Permission.DOCUMENTS_READ,
                    Permission.KNOWLEDGE_QUERY,
                }
            ),
            Role.CONTRIBUTOR: frozenset(
                {
                    Permission.DOCUMENTS_READ,
                    Permission.DOCUMENTS_UPLOAD,
                    Permission.KNOWLEDGE_QUERY,
                }
            ),
            Role.ANALYST: frozenset(
                {
                    Permission.DOCUMENTS_READ,
                    Permission.DOCUMENTS_UPLOAD,
                    Permission.KNOWLEDGE_QUERY,
                    Permission.AGENT_EXECUTE,
                    Permission.AGENT_APPROVE,
                }
            ),
            Role.ADMIN: frozenset(
                {
                    Permission.USERS_READ,
                    Permission.USERS_MANAGE,
                    Permission.DOCUMENTS_READ,
                    Permission.DOCUMENTS_UPLOAD,
                    Permission.DOCUMENTS_DELETE,
                    Permission.KNOWLEDGE_QUERY,
                    Permission.KNOWLEDGE_ADMIN,
                    Permission.AGENT_EXECUTE,
                    Permission.AGENT_APPROVE,
                }
            ),
            Role.SUPER_ADMIN: frozenset(Permission),
        }
        return mapping[self]

    def has_permission(self, permission: str) -> bool:
        """Check if role grants the given permission string."""
        try:
            perm = Permission(permission)
        except ValueError:
            return False
        return perm in self.permissions
