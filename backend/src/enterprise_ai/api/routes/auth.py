"""Authentication API routes."""

from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from enterprise_ai.application.dto.auth import (
    LoginRequestDTO,
    RefreshTokenRequestDTO,
    RegisterRequestDTO,
    TokenResponseDTO,
    UserResponseDTO,
)
from enterprise_ai.application.services.auth_service import AuthService
from enterprise_ai.api.dependencies import get_auth_service, get_current_user
from enterprise_ai.domain.entities.user import User

router = APIRouter(prefix="/auth", tags=["Authentication"])
security = HTTPBearer()


@router.post("/register", response_model=UserResponseDTO, status_code=status.HTTP_201_CREATED)
async def register(
    request: RegisterRequestDTO,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> UserResponseDTO:
    """Register a new user account."""
    return await auth_service.register(request)


@router.post("/login", response_model=TokenResponseDTO)
async def login(
    request: LoginRequestDTO,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> TokenResponseDTO:
    """Authenticate and receive JWT tokens."""
    return await auth_service.login(request)


@router.post("/refresh", response_model=TokenResponseDTO)
async def refresh(
    request: RefreshTokenRequestDTO,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> TokenResponseDTO:
    """Refresh access token using a valid refresh token."""
    return await auth_service.refresh_token(request.refresh_token)


@router.get("/me", response_model=UserResponseDTO)
async def get_me(
    current_user: Annotated[User, Depends(get_current_user)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> UserResponseDTO:
    """Get the currently authenticated user."""
    return AuthService.to_response(current_user)
