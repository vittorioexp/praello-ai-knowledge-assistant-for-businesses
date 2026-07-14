"""JWT token creation and validation."""

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from jose import JWTError, jwt
from pydantic import BaseModel

from enterprise_ai.domain.exceptions import AuthenticationError
from enterprise_ai.infrastructure.config.settings import Settings


class TokenPayload(BaseModel):
    """Decoded JWT payload."""

    sub: UUID
    email: str
    role: str
    type: str
    exp: datetime


class JWTService:
    """Handles JWT access and refresh token lifecycle."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def create_access_token(
        self,
        *,
        user_id: UUID,
        email: str,
        role: str,
    ) -> str:
        expire = datetime.now(UTC) + timedelta(
            minutes=self._settings.jwt_access_token_expire_minutes
        )
        payload = {
            "sub": str(user_id),
            "email": email,
            "role": role,
            "type": "access",
            "exp": expire,
        }
        return jwt.encode(
            payload,
            self._settings.jwt_secret_key,
            algorithm=self._settings.jwt_algorithm,
        )

    def create_refresh_token(
        self,
        *,
        user_id: UUID,
        email: str,
        role: str,
    ) -> str:
        expire = datetime.now(UTC) + timedelta(
            days=self._settings.jwt_refresh_token_expire_days
        )
        payload = {
            "sub": str(user_id),
            "email": email,
            "role": role,
            "type": "refresh",
            "exp": expire,
        }
        return jwt.encode(
            payload,
            self._settings.jwt_secret_key,
            algorithm=self._settings.jwt_algorithm,
        )

    def decode_token(self, token: str, *, expected_type: str = "access") -> TokenPayload:
        """Decode and validate a JWT token."""
        try:
            payload: dict[str, Any] = jwt.decode(
                token,
                self._settings.jwt_secret_key,
                algorithms=[self._settings.jwt_algorithm],
            )
            if payload.get("type") != expected_type:
                raise AuthenticationError("Invalid token type")
            return TokenPayload(
                sub=UUID(payload["sub"]),
                email=payload["email"],
                role=payload["role"],
                type=payload["type"],
                exp=datetime.fromtimestamp(payload["exp"], tz=UTC),
            )
        except JWTError as exc:
            raise AuthenticationError("Invalid or expired token") from exc
