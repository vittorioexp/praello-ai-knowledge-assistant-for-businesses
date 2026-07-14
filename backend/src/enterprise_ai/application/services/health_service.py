"""Health check use case."""

import time
from datetime import UTC, datetime

from enterprise_ai import __version__
from enterprise_ai.application.dto.health import ComponentHealthDTO, HealthStatusDTO, ReadinessDTO
from enterprise_ai.infrastructure.cache.redis_client import RedisClient
from enterprise_ai.infrastructure.config.settings import Settings
from enterprise_ai.infrastructure.database.session import Database
from enterprise_ai.infrastructure.logging.setup import get_logger

logger = get_logger(__name__)


class HealthService:
    """Application service for health and readiness probes."""

    def __init__(
        self,
        settings: Settings,
        database: Database,
        redis: RedisClient,
    ) -> None:
        self._settings = settings
        self._database = database
        self._redis = redis

    def liveness(self) -> HealthStatusDTO:
        """Return liveness status — process is running."""
        return HealthStatusDTO(
            status="healthy",
            version=__version__,
            environment=self._settings.app_env,
            timestamp=datetime.now(UTC),
        )

    async def readiness(self) -> ReadinessDTO:
        """Return readiness status — dependencies are available."""
        checks: list[ComponentHealthDTO] = []

        db_start = time.perf_counter()
        db_healthy = await self._database.health_check()
        db_latency = (time.perf_counter() - db_start) * 1000
        checks.append(
            ComponentHealthDTO(
                name="postgresql",
                status="healthy" if db_healthy else "unhealthy",
                latency_ms=round(db_latency, 2),
                message=None if db_healthy else "Database connection failed",
            )
        )

        redis_start = time.perf_counter()
        redis_healthy = await self._redis.health_check()
        redis_latency = (time.perf_counter() - redis_start) * 1000
        checks.append(
            ComponentHealthDTO(
                name="redis",
                status="healthy" if redis_healthy else "unhealthy",
                latency_ms=round(redis_latency, 2),
                message=None if redis_healthy else "Redis connection failed",
            )
        )

        all_healthy = all(c.status == "healthy" for c in checks)
        status = "ready" if all_healthy else "not_ready"

        if not all_healthy:
            logger.warning("readiness_check_failed", checks=[c.model_dump() for c in checks])

        return ReadinessDTO(status=status, checks=checks)
