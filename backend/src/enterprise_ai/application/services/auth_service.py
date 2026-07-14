"""Authentication application service."""

from uuid import UUID

from enterprise_ai.application.dto.auth import (
    LoginRequestDTO,
    RegisterRequestDTO,
    TokenResponseDTO,
    UserResponseDTO,
)
from enterprise_ai.domain.entities.user import User
from enterprise_ai.domain.exceptions import AuthenticationError, AuthorizationError, ValidationError
from enterprise_ai.domain.repositories.user_repository import UserRepository
from enterprise_ai.domain.value_objects.role import Role
from enterprise_ai.infrastructure.config.settings import Settings
from enterprise_ai.infrastructure.security.jwt import JWTService
from enterprise_ai.infrastructure.security.password import hash_password, verify_password


class AuthService:
    """Handles user registration, authentication, and token management."""

    def __init__(
        self,
        user_repository: UserRepository,
        jwt_service: JWTService,
        settings: Settings,
    ) -> None:
        self._users = user_repository
        self._jwt = jwt_service
        self._settings = settings

    async def register(self, request: RegisterRequestDTO) -> UserResponseDTO:
        """Register a new user."""
        existing = await self._users.get_by_email(request.email)
        if existing:
            raise ValidationError("Email already registered")

        user = User(
            email=request.email,
            hashed_password=hash_password(request.password),
            full_name=request.full_name,
            role=Role.VIEWER,
        )
        created = await self._users.create(user)
        return self._to_response(created)

    async def login(self, request: LoginRequestDTO) -> TokenResponseDTO:
        """Authenticate user and return JWT tokens."""
        user = await self._users.get_by_email(request.email)
        if not user or not verify_password(request.password, user.hashed_password):
            raise AuthenticationError("Invalid email or password")
        if not user.is_active:
            raise AuthenticationError("Account is deactivated")

        return TokenResponseDTO(
            access_token=self._jwt.create_access_token(
                user_id=user.id, email=user.email, role=user.role.value
            ),
            refresh_token=self._jwt.create_refresh_token(
                user_id=user.id, email=user.email, role=user.role.value
            ),
        )

    async def refresh_token(self, refresh_token: str) -> TokenResponseDTO:
        """Issue new tokens from a valid refresh token."""
        payload = self._jwt.decode_token(refresh_token, expected_type="refresh")
        user = await self._users.get_by_id(payload.sub)
        if not user or not user.is_active:
            raise AuthenticationError("User not found or inactive")

        return TokenResponseDTO(
            access_token=self._jwt.create_access_token(
                user_id=user.id, email=user.email, role=user.role.value
            ),
            refresh_token=self._jwt.create_refresh_token(
                user_id=user.id, email=user.email, role=user.role.value
            ),
        )

    async def get_current_user(self, user_id: UUID) -> User:
        """Load the authenticated user."""
        user = await self._users.get_by_id(user_id)
        if not user or not user.is_active:
            raise AuthenticationError("User not found or inactive")
        return user

    def require_permission(self, user: User, permission: str) -> None:
        """Raise if user lacks the required permission."""
        if not user.has_permission(permission):
            raise AuthorizationError(
                f"Permission '{permission}' required",
                details={"role": user.role.value},
            )

    @staticmethod
    def to_response(user: User) -> UserResponseDTO:
        return UserResponseDTO(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            role=user.role,
            is_active=user.is_active,
        )

    def _to_response(self, user: User) -> UserResponseDTO:
        return self.to_response(user)
