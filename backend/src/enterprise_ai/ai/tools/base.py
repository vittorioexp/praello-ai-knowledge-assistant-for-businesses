"""Base tool interface and registry."""

from abc import ABC, abstractmethod
from typing import Any

from enterprise_ai.domain.value_objects.agent import ToolRiskLevel


class AgentTool(ABC):
    """Base class for agent tools."""

    name: str
    description: str
    risk_level: ToolRiskLevel = ToolRiskLevel.LOW
    requires_approval: bool = False

    @abstractmethod
    async def execute(self, **kwargs: Any) -> str:
        ...

    def schema(self) -> dict[str, Any]:
        """Return tool schema for the agent."""
        return {
            "name": self.name,
            "description": self.description,
            "risk_level": self.risk_level.value,
            "requires_approval": self.requires_approval,
        }


class ToolRegistry:
    """Registry of available agent tools."""

    def __init__(self) -> None:
        self._tools: dict[str, AgentTool] = {}

    def register(self, tool: AgentTool) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> AgentTool | None:
        return self._tools.get(name)

    def list_tools(self) -> list[dict[str, Any]]:
        return [tool.schema() for tool in self._tools.values()]

    async def execute(self, name: str, arguments: dict[str, Any]) -> str:
        tool = self.get(name)
        if tool is None:
            return f"Error: unknown tool '{name}'"
        return await tool.execute(**arguments)
