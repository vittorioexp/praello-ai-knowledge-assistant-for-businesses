"""RBAC permission enforcement dependency."""

from collections.abc import Callable
from typing import Annotated

from fastapi import Depends

from enterprise_ai.api.dependencies import get_auth_service, get_current_user
from enterprise_ai.application.services.auth_service import AuthService
from enterprise_ai.domain.entities.user import User


def require_permission(permission: str) -> Callable:
    """Create a dependency that enforces a specific permission."""

    async def _check(
        current_user: Annotated[User, Depends(get_current_user)],
        auth_service: Annotated[AuthService, Depends(get_auth_service)],
    ) -> User:
        auth_service.require_permission(current_user, permission)
        return current_user

    return _check
