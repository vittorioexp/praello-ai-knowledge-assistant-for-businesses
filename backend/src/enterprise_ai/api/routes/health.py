"""Health check API routes."""

from typing import Annotated

from fastapi import APIRouter, Depends, Response, status

from enterprise_ai.application.dto.health import HealthStatusDTO, ReadinessDTO
from enterprise_ai.application.services.health_service import HealthService
from enterprise_ai.api.dependencies import get_health_service

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("/live", response_model=HealthStatusDTO)
async def liveness(
    health_service: Annotated[HealthService, Depends(get_health_service)],
) -> HealthStatusDTO:
    """Kubernetes liveness probe — process is alive."""
    return health_service.liveness()


@router.get("/ready", response_model=ReadinessDTO)
async def readiness(
    response: Response,
    health_service: Annotated[HealthService, Depends(get_health_service)],
) -> ReadinessDTO:
    """Kubernetes readiness probe — dependencies are ready."""
    result = await health_service.readiness()
    if result.status != "ready":
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return result
