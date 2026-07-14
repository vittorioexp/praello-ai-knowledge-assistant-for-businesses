"""Tests for authentication service."""

import pytest

from enterprise_ai.application.dto.auth import LoginRequestDTO, RegisterRequestDTO
from enterprise_ai.application.services.auth_service import AuthService
from enterprise_ai.domain.exceptions import AuthenticationError, ValidationError
from enterprise_ai.infrastructure.repositories.user_repository import SQLAlchemyUserRepository
from enterprise_ai.infrastructure.security.jwt import JWTService


@pytest.fixture
def auth_service(db_session, test_settings) -> AuthService:
    return AuthService(
        SQLAlchemyUserRepository(db_session),
        JWTService(test_settings),
        test_settings,
    )


@pytest.mark.asyncio
async def test_register_creates_user(auth_service: AuthService) -> None:
    result = await auth_service.register(
        RegisterRequestDTO(
            email="test@company.com",
            password="password123",
            full_name="Test User",
        )
    )
    assert result.email == "test@company.com"
    assert result.role.value == "viewer"


@pytest.mark.asyncio
async def test_register_duplicate_raises(auth_service: AuthService) -> None:
    dto = RegisterRequestDTO(
        email="dup@company.com",
        password="password123",
        full_name="Dup User",
    )
    await auth_service.register(dto)
    with pytest.raises(ValidationError, match="already registered"):
        await auth_service.register(dto)


@pytest.mark.asyncio
async def test_login_returns_tokens(auth_service: AuthService) -> None:
    await auth_service.register(
        RegisterRequestDTO(
            email="login@company.com",
            password="password123",
            full_name="Login User",
        )
    )
    tokens = await auth_service.login(
        LoginRequestDTO(email="login@company.com", password="password123")
    )
    assert tokens.access_token
    assert tokens.refresh_token


@pytest.mark.asyncio
async def test_login_wrong_password(auth_service: AuthService) -> None:
    await auth_service.register(
        RegisterRequestDTO(
            email="wrong@company.com",
            password="password123",
            full_name="Wrong User",
        )
    )
    with pytest.raises(AuthenticationError):
        await auth_service.login(
            LoginRequestDTO(email="wrong@company.com", password="badpassword")
        )


@pytest.mark.asyncio
async def test_require_permission_denied(auth_service: AuthService) -> None:
    user = await auth_service.register(
        RegisterRequestDTO(
            email="perm@company.com",
            password="password123",
            full_name="Perm User",
        )
    )
    from enterprise_ai.domain.exceptions import AuthorizationError

    domain_user = await auth_service.get_current_user(user.id)
    with pytest.raises(AuthorizationError):
        auth_service.require_permission(domain_user, "users:manage")
