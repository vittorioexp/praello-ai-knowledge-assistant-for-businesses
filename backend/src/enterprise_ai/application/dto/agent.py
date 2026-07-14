"""Agent request/response DTOs."""

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from enterprise_ai.domain.value_objects.agent import AgentStatus, ToolCall


class AgentMessageRequestDTO(BaseModel):
    """Send a message to the agent."""

    message: str = Field(min_length=1, max_length=4000)
    thread_id: UUID | None = None


class AgentApprovalRequestDTO(BaseModel):
    """Approve or reject a pending agent action."""

    approved: bool = True
    reason: str | None = None


class AgentToolResultDTO(BaseModel):
    """Result from a tool execution."""

    tool_call_id: str
    tool_name: str
    output: str
    success: bool = True


class AgentResponseDTO(BaseModel):
    """Structured agent response."""

    thread_id: UUID
    status: AgentStatus
    answer: str
    confidence: float = Field(ge=0.0, le=1.0, default=0.0)
    tool_calls: list[ToolCall] = Field(default_factory=list)
    tool_results: list[AgentToolResultDTO] = Field(default_factory=list)
    requires_approval: bool = False
    pending_action: dict[str, Any] | None = None
    messages: list[dict[str, str]] = Field(default_factory=list)
