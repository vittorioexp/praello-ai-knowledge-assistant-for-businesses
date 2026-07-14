"""Tool registry factory."""

from enterprise_ai.ai.tools.email import EmailTool
from enterprise_ai.ai.tools.filesystem import FilesystemSearchTool
from enterprise_ai.ai.tools.github import GitHubTool
from enterprise_ai.ai.tools.knowledge import KnowledgeSearchTool
from enterprise_ai.ai.tools.rest_api import RestAPITool
from enterprise_ai.ai.tools.slack import SlackTool
from enterprise_ai.ai.tools.sql_search import SQLSearchTool
from enterprise_ai.ai.tools.base import ToolRegistry
from enterprise_ai.application.services.rag_service import RAGService
from enterprise_ai.domain.entities.user import User
from enterprise_ai.infrastructure.config.settings import Settings
from sqlalchemy.ext.asyncio import AsyncSession


def build_tool_registry(
    *,
    rag_service: RAGService,
    user: User,
    session: AsyncSession,
    settings: Settings,
) -> ToolRegistry:
    """Build the tool registry for an agent session."""
    registry = ToolRegistry()
    registry.register(KnowledgeSearchTool(rag_service, user))
    registry.register(SQLSearchTool(session))
    registry.register(FilesystemSearchTool(settings))
    registry.register(RestAPITool())
    registry.register(GitHubTool(settings))
    registry.register(SlackTool())
    registry.register(EmailTool())
    return registry
