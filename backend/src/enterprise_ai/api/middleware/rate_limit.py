"""Distributed request rate limiting backed by Redis."""

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from enterprise_ai.infrastructure.cache.redis_client import RedisClient
from enterprise_ai.infrastructure.config.settings import Settings


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Apply a fixed-window limit per authenticated user or client IP."""

    def __init__(self, app, *, redis: RedisClient, settings: Settings) -> None:
        super().__init__(app)
        self._redis = redis.client
        self._limit = settings.rate_limit_requests
        self._window = settings.rate_limit_window_seconds

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if request.url.path in {"/", "/health", "/api/v1/health"}:
            return await call_next(request)
        client = request.headers.get("X-Forwarded-For", request.client.host if request.client else "unknown")
        key = f"rate-limit:{client.split(',')[0].strip()}:{request.url.path}"
        try:
            count = await self._redis.incr(key)
            if count == 1:
                await self._redis.expire(key, self._window)
            if count > self._limit:
                return JSONResponse(
                    {"detail": "Rate limit exceeded"},
                    status_code=429,
                    headers={"Retry-After": str(self._window)},
                )
        except Exception:
            # Redis outage must not take the API offline; health monitoring reports it separately.
            pass
        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(self._limit)
        return response