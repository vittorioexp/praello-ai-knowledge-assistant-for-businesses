"""Operational administration endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from enterprise_ai.api.dependencies import get_ingestion_queue
from enterprise_ai.api.middleware.rbac import require_permission
from enterprise_ai.domain.entities.user import User
from enterprise_ai.domain.value_objects.role import Permission
from enterprise_ai.infrastructure.queue.ingestion_queue import IngestionQueue

router = APIRouter(prefix="/operations", tags=["Operations"])


@router.post("/ingestion/replay-dead-letters")
async def replay_ingestion_dead_letters(
    queue: Annotated[IngestionQueue, Depends(get_ingestion_queue)],
    _current_user: Annotated[User, Depends(require_permission(Permission.KNOWLEDGE_ADMIN.value))],
    count: Annotated[int, Query(ge=1, le=1000)] = 100,
) -> dict[str, int]:
    """Replay a bounded number of permanently failed ingestion jobs."""
    return {"replayed": await queue.replay_dead_letters(count=count)}