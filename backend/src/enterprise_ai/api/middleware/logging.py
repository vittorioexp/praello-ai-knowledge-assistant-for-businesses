"""Request logging middleware."""

import time
import uuid
from uuid import UUID

import structlog
from jose import JWTError, jwt
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from enterprise_ai.infrastructure.logging.setup import get_logger
from enterprise_ai.infrastructure.database.models.audit_event import AuditEventModel

logger = get_logger(__name__)
AUDIT_PATHS = ("/auth/", "/connectors", "/documents", "/operations")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log request/response metadata with correlation ID."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
        )

        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start) * 1000

        logger.info(
            "request_completed",
            status_code=response.status_code,
            duration_ms=round(duration_ms, 2),
        )

        if any(request.url.path.startswith(path) for path in AUDIT_PATHS):
            logger.info(
                "audit_event",
                actor_id=_actor_id(request),
                action=f"{request.method} {request.url.path}",
                status_code=response.status_code,
                outcome="success" if response.status_code < 400 else "failure",
            )
            try:
                actor = _actor_id(request)
                async for session in request.app.state.database.session():
                    session.add(
                        AuditEventModel(
                            request_id=request_id,
                            actor_id=UUID(actor) if actor else None,
                            action=f"{request.method} {request.url.path}",
                            method=request.method,
                            path=request.url.path,
                            status_code=response.status_code,
                            outcome="success" if response.status_code < 400 else "failure",
                            client_ip=request.client.host if request.client else None,
                        )
                    )
            except Exception as exc:
                logger.warning("audit_persistence_failed", error=str(exc))

        response.headers["X-Request-ID"] = request_id
        return response


def _actor_id(request: Request) -> str | None:
    """Extract only the JWT subject for audit correlation, never the token itself."""
    authorization = request.headers.get("Authorization", "")
    if not authorization.startswith("Bearer "):
        return None
    try:
        claims = jwt.get_unverified_claims(authorization[7:])
        return str(claims.get("sub")) if claims.get("sub") else None
    except (JWTError, ValueError):
        return None
