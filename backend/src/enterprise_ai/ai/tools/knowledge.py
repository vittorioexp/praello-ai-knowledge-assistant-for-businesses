"""Knowledge base search tool."""

from enterprise_ai.ai.tools.base import AgentTool
from enterprise_ai.application.dto.rag import RAGQueryRequestDTO
from enterprise_ai.application.services.rag_service import RAGService
from enterprise_ai.domain.entities.user import User
from enterprise_ai.domain.value_objects.agent import ToolRiskLevel


class KnowledgeSearchTool(AgentTool):
    """Search the enterprise knowledge base via RAG."""

    name = "knowledge_search"
    description = "Search uploaded documents and policies in the knowledge base."
    risk_level = ToolRiskLevel.LOW
    requires_approval = False

    def __init__(self, rag_service: RAGService, user: User) -> None:
        self._rag = rag_service
        self._user = user

    async def execute(self, *, query: str, **kwargs) -> str:
        result = await self._rag.query(
            RAGQueryRequestDTO(query=query, use_multi_query=True, use_reranking=True),
            self._user,
        )
        sources = ", ".join(s.document_name for s in result.sources[:3])
        return (
            f"Answer: {result.answer}\n"
            f"Confidence: {result.confidence}\n"
            f"Sources: {sources or 'none'}"
        )
