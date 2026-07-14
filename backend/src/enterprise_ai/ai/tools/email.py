"""Email integration abstraction."""

from enterprise_ai.ai.tools.base import AgentTool
from enterprise_ai.domain.value_objects.agent import ToolRiskLevel


class EmailTool(AgentTool):
    """Email sending abstraction."""

    name = "email"
    description = "Send emails to recipients. Requires human approval."
    risk_level = ToolRiskLevel.HIGH
    requires_approval = True

    async def execute(self, *, to: str, subject: str, body: str, **kwargs) -> str:
        return f"[Email stub] Would send to {to}: '{subject}' — {body[:100]}"
