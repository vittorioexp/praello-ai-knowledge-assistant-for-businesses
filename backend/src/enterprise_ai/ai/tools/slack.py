"""Slack integration abstraction."""

from enterprise_ai.ai.tools.base import AgentTool
from enterprise_ai.domain.value_objects.agent import ToolRiskLevel


class SlackTool(AgentTool):
    """Slack messaging abstraction."""

    name = "slack"
    description = "Send messages to Slack channels. Requires human approval."
    risk_level = ToolRiskLevel.HIGH
    requires_approval = True

    async def execute(self, *, channel: str, message: str, **kwargs) -> str:
        return f"[Slack stub] Would send to #{channel}: {message[:200]}"
