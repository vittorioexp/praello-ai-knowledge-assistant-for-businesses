"""Tests for health service."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from enterprise_ai.application.services.health_service import HealthService
from enterprise_ai.infrastructure.config.settings import Settings


@pytest.fixture
def health_service() -> HealthService:
    settings = Settings(
        app_env="test",
        app_secret_key="test-secret-key-minimum-32-chars-long",
        jwt_secret_key="test-jwt-secret-key-min-32-chars",
    )
    database = MagicMock()
    database.health_check = AsyncMock(return_value=True)
    redis = MagicMock()
    redis.health_check = AsyncMock(return_value=True)
    return HealthService(settings, database, redis)


def test_liveness(health_service: HealthService) -> None:
    result = health_service.liveness()
    assert result.status == "healthy"
    assert result.environment == "test"


@pytest.mark.asyncio
async def test_readiness_all_healthy(health_service: HealthService) -> None:
    result = await health_service.readiness()
    assert result.status == "ready"
    assert all(c.status == "healthy" for c in result.checks)


@pytest.mark.asyncio
async def test_readiness_db_unhealthy() -> None:
    settings = Settings(
        app_env="test",
        app_secret_key="test-secret-key-minimum-32-chars-long",
        jwt_secret_key="test-jwt-secret-key-min-32-chars",
    )
    database = MagicMock()
    database.health_check = AsyncMock(return_value=False)
    redis = MagicMock()
    redis.health_check = AsyncMock(return_value=True)
    service = HealthService(settings, database, redis)

    result = await service.readiness()
    assert result.status == "not_ready"
    db_check = next(c for c in result.checks if c.name == "postgresql")
    assert db_check.status == "unhealthy"
