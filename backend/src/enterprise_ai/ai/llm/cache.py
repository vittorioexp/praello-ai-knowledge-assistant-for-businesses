"""Redis-backed LLM response cache."""

import hashlib
import json

from enterprise_ai.infrastructure.cache.redis_client import RedisClient
from enterprise_ai.infrastructure.config.settings import Settings
from enterprise_ai.infrastructure.logging.setup import get_logger

logger = get_logger(__name__)


class LLMCache:
    """Caches LLM responses in Redis to reduce cost and latency."""

    PREFIX = "llm:cache:"
    DEFAULT_TTL = 3600

    def __init__(self, redis: RedisClient, settings: Settings) -> None:
        self._redis = redis
        self._enabled = not settings.is_test and settings.llm_cache_enabled
        self._ttl = settings.llm_cache_ttl_seconds

    def _cache_key(self, model: str, system_prompt: str, user_prompt: str) -> str:
        payload = json.dumps({"model": model, "system": system_prompt, "user": user_prompt})
        digest = hashlib.sha256(payload.encode()).hexdigest()
        return f"{self.PREFIX}{digest}"

    async def get(self, model: str, system_prompt: str, user_prompt: str) -> str | None:
        if not self._enabled:
            return None
        try:
            key = self._cache_key(model, system_prompt, user_prompt)
            value = await self._redis.client.get(key)
            if value:
                logger.info("llm_cache_hit", model=model)
            return value
        except Exception:
            return None

    async def set(self, model: str, system_prompt: str, user_prompt: str, response: str) -> None:
        if not self._enabled:
            return
        try:
            key = self._cache_key(model, system_prompt, user_prompt)
            await self._redis.client.setex(key, self._ttl, response)
        except Exception:
            logger.warning("llm_cache_set_failed")
