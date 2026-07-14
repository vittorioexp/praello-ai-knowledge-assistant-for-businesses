"""Agent conversation API routes."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from enterprise_ai.api.dependencies import get_agent_service
from enterprise_ai.api.middleware.rbac import require_permission
from enterprise_ai.application.dto.agent import (
    AgentApprovalRequestDTO,
    AgentMessageRequestDTO,
    AgentResponseDTO,
)
from enterprise_ai.application.services.agent_service import AgentService
from enterprise_ai.domain.entities.user import User
from enterprise_ai.domain.value_objects.role import Permission

router = APIRouter(prefix="/agent", tags=["Agent"])


@router.post("/conversations", response_model=AgentResponseDTO)
async def send_message(
    request: AgentMessageRequestDTO,
    agent_service: Annotated[AgentService, Depends(get_agent_service)],
    current_user: Annotated[User, Depends(require_permission(Permission.AGENT_EXECUTE.value))],
) -> AgentResponseDTO:
    """Send a message to the LangGraph agent."""
    return await agent_service.send_message(request, current_user)


@router.post("/conversations/{thread_id}/approve", response_model=AgentResponseDTO)
async def approve_action(
    thread_id: UUID,
    request: AgentApprovalRequestDTO,
    agent_service: Annotated[AgentService, Depends(get_agent_service)],
    current_user: Annotated[User, Depends(require_permission(Permission.AGENT_APPROVE.value))],
) -> AgentResponseDTO:
    """Approve or reject a pending agent action."""
    return await agent_service.approve_action(thread_id, request, current_user)


@router.get("/conversations/{thread_id}", response_model=AgentResponseDTO)
async def get_conversation(
    thread_id: UUID,
    agent_service: Annotated[AgentService, Depends(get_agent_service)],
    _current_user: Annotated[User, Depends(require_permission(Permission.AGENT_EXECUTE.value))],
) -> AgentResponseDTO:
    """Get conversation state from checkpoint."""
    return await agent_service.get_conversation(thread_id)
