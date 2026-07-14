"""Agent-related value objects."""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class AgentStatus(str, Enum):
    """Agent execution status."""

    RUNNING = "running"
    AWAITING_APPROVAL = "awaiting_approval"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"


class ToolRiskLevel(str, Enum):
    """Risk classification for agent tools."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ToolCall(BaseModel):
    """A tool invocation requested by the agent."""

    id: str
    name: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    requires_approval: bool = False
    risk_level: ToolRiskLevel = ToolRiskLevel.LOW


class AgentMessage(BaseModel):
    """A message in an agent conversation."""

    role: str
    content: str
    tool_calls: list[ToolCall] = Field(default_factory=list)
