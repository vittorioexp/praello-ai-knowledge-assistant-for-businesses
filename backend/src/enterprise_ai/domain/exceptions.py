"""Domain exceptions."""

from typing import Any


class DomainError(Exception):
    """Base domain exception."""

    def __init__(self, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class EntityNotFoundError(DomainError):
    """Raised when a requested entity does not exist."""


class AuthenticationError(DomainError):
    """Raised on authentication failure."""


class AuthorizationError(DomainError):
    """Raised when user lacks required permissions."""


class ValidationError(DomainError):
    """Raised on domain validation failure."""
