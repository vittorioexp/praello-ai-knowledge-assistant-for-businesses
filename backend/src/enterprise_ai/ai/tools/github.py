"""GitHub integration abstraction."""

from enterprise_ai.ai.tools.base import AgentTool
from enterprise_ai.domain.value_objects.agent import ToolRiskLevel
from enterprise_ai.infrastructure.config.settings import Settings


class GitHubTool(AgentTool):
    """GitHub API abstraction for repository operations."""

    name = "github"
    description = (
        "Interact with GitHub repositories (list issues, PRs). Requires approval."
    )
    risk_level = ToolRiskLevel.HIGH
    requires_approval = True

    def __init__(self, settings: Settings) -> None:
        self._token = getattr(settings, "github_token", "") or ""

    async def execute(self, *, action: str, repo: str, **kwargs) -> str:
        if not self._token:
            return f"[GitHub stub] Would execute '{action}' on {repo} (no token configured)"
        return f"[GitHub stub] Executed '{action}' on {repo}"
