"""REST API tool with approval gate."""

import httpx

from enterprise_ai.ai.tools.base import AgentTool
from enterprise_ai.domain.value_objects.agent import ToolRiskLevel


class RestAPITool(AgentTool):
    """Make HTTP requests to external REST APIs."""

    name = "rest_api"
    description = "Call external REST APIs. Requires human approval before execution."
    risk_level = ToolRiskLevel.HIGH
    requires_approval = True

    async def execute(self, *, url: str, method: str = "GET", body: str | None = None, **kwargs) -> str:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.request(method.upper(), url, content=body)
            return f"Status: {response.status_code}\nBody: {response.text[:1000]}"
