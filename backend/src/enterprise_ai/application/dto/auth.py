"""Authentication DTOs."""

from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

from enterprise_ai.domain.value_objects.role import Role


class RegisterRequestDTO(BaseModel):
    """User registration request."""

    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=1, max_length=255)


class LoginRequestDTO(BaseModel):
    """User login request."""

    email: EmailStr
    password: str


class TokenResponseDTO(BaseModel):
    """JWT token pair response."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshTokenRequestDTO(BaseModel):
    """Refresh token request."""

    refresh_token: str


class UserResponseDTO(BaseModel):
    """Public user representation."""

    id: UUID
    email: EmailStr
    full_name: str
    role: Role
    is_active: bool
