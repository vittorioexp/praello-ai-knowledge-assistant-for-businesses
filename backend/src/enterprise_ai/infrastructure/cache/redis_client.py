"""Redis client infrastructure."""

from redis.asyncio import Redis

from enterprise_ai.infrastructure.config.settings import Settings


class RedisClient:
    """Async Redis connection wrapper."""

    def __init__(self, settings: Settings) -> None:
        self._client = Redis.from_url(str(settings.redis_url), decode_responses=True)

    @property
    def client(self) -> Redis:
        return self._client

    async def health_check(self) -> bool:
        """Verify Redis connectivity."""
        try:
            return await self._client.ping()
        except Exception:
            return False

    async def close(self) -> None:
        """Close Redis connection."""
        await self._client.aclose()
