"""LLM operations API routes."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request

from enterprise_ai.api.middleware.rbac import require_permission
from enterprise_ai.domain.entities.user import User
from enterprise_ai.domain.value_objects.role import Permission

router = APIRouter(prefix="/llm", tags=["LLMOps"])


@router.get("/usage")
async def get_llm_usage(
    request: Request,
    _current_user: Annotated[User, Depends(require_permission(Permission.KNOWLEDGE_ADMIN.value))],
) -> dict:
    """Get LLM usage statistics and cost summary."""
    tracker = request.app.state.llm_tracker
    return tracker.get_summary()
