"""Application DTOs."""

from datetime import UTC, datetime

from pydantic import BaseModel, Field


class HealthStatusDTO(BaseModel):
    """Health check response."""

    status: str
    version: str
    environment: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ComponentHealthDTO(BaseModel):
    """Individual component health."""

    name: str
    status: str
    latency_ms: float | None = None
    message: str | None = None


class ReadinessDTO(BaseModel):
    """Readiness probe response."""

    status: str
    checks: list[ComponentHealthDTO]
