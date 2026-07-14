"""Agent application service."""

from uuid import UUID, uuid4

from langgraph.checkpoint.memory import MemorySaver

from enterprise_ai.ai.agents.graph import build_agent_graph
from enterprise_ai.ai.agents.nodes import _get_message_content, _get_message_role
from enterprise_ai.ai.tools.factory import build_tool_registry
from enterprise_ai.application.dto.agent import (
    AgentApprovalRequestDTO,
    AgentMessageRequestDTO,
    AgentResponseDTO,
    AgentToolResultDTO,
)
from enterprise_ai.application.services.rag_service import RAGService
from enterprise_ai.domain.entities.user import User
from enterprise_ai.domain.exceptions import ValidationError
from enterprise_ai.domain.repositories.llm_service import LLMService
from enterprise_ai.domain.value_objects.agent import AgentStatus, ToolCall, ToolRiskLevel
from enterprise_ai.infrastructure.config.settings import Settings
from enterprise_ai.infrastructure.logging.setup import get_logger
from sqlalchemy.ext.asyncio import AsyncSession

logger = get_logger(__name__)


class AgentService:
    """Manages LangGraph agent conversations with checkpointing."""

    def __init__(
        self,
        llm_service: LLMService,
        rag_service: RAGService,
        session: AsyncSession,
        settings: Settings,
        checkpointer: MemorySaver | None = None,
    ) -> None:
        self._llm = llm_service
        self._rag = rag_service
        self._session = session
        self._settings = settings
        self._checkpointer = checkpointer or MemorySaver()

    async def send_message(
        self,
        request: AgentMessageRequestDTO,
        user: User,
    ) -> AgentResponseDTO:
        """Send a message and run the agent graph."""
        thread_id = request.thread_id or uuid4()
        registry = build_tool_registry(
            rag_service=self._rag,
            user=user,
            session=self._session,
            settings=self._settings,
        )
        graph = build_agent_graph(
            self._llm, registry, self._settings, self._checkpointer
        )

        config = {"configurable": {"thread_id": str(thread_id)}}
        input_state = {
            "messages": [{"role": "user", "content": request.message}],
            "user_id": str(user.id),
            "thread_id": str(thread_id),
            "retry_count": 0,
            "tool_call_count": 0,
            "pending_tool": None,
            "approval_granted": False,
            "tool_results": [],
            "final_answer": "",
            "confidence": 0.0,
            "status": "running",
            "blocked": False,
            "error": None,
        }

        result = await graph.ainvoke(input_state, config)
        return self._to_response(thread_id, result)

    async def approve_action(
        self,
        thread_id: UUID,
        request: AgentApprovalRequestDTO,
        user: User,
    ) -> AgentResponseDTO:
        """Resume agent after human approval."""
        if not request.approved:
            return AgentResponseDTO(
                thread_id=thread_id,
                status=AgentStatus.COMPLETED,
                answer="Action was rejected by the user.",
                confidence=1.0,
            )

        registry = build_tool_registry(
            rag_service=self._rag,
            user=user,
            session=self._session,
            settings=self._settings,
        )
        graph = build_agent_graph(
            self._llm, registry, self._settings, self._checkpointer
        )
        config = {"configurable": {"thread_id": str(thread_id)}}

        snapshot = await graph.aget_state(config)
        if not snapshot or not snapshot.values.get("pending_tool"):
            raise ValidationError("No pending action to approve")

        result = await graph.ainvoke(
            {"approval_granted": True, "status": "running"},
            config,
        )
        return self._to_response(thread_id, result)

    async def get_conversation(self, thread_id: UUID) -> AgentResponseDTO:
        """Get current conversation state from checkpoint."""
        from enterprise_ai.ai.tools.base import ToolRegistry

        graph = build_agent_graph(
            self._llm,
            ToolRegistry(),
            self._settings,
            self._checkpointer,
        )
        config = {"configurable": {"thread_id": str(thread_id)}}
        snapshot = await graph.aget_state(config)
        if not snapshot or not snapshot.values:
            raise ValidationError(f"Conversation {thread_id} not found")
        return self._to_response(thread_id, snapshot.values)

    @staticmethod
    def _to_response(thread_id: UUID, state: dict) -> AgentResponseDTO:
        status_map = {
            "running": AgentStatus.RUNNING,
            "awaiting_approval": AgentStatus.AWAITING_APPROVAL,
            "completed": AgentStatus.COMPLETED,
            "failed": AgentStatus.FAILED,
            "blocked": AgentStatus.BLOCKED,
        }
        pending = state.get("pending_tool")
        tool_calls = []
        if pending:
            tool_calls.append(
                ToolCall(
                    id=pending.get("id", ""),
                    name=pending.get("name", ""),
                    arguments=pending.get("arguments", {}),
                    requires_approval=pending.get("requires_approval", False),
                    risk_level=ToolRiskLevel.HIGH if pending.get("requires_approval") else ToolRiskLevel.LOW,
                )
            )

        tool_results = [
            AgentToolResultDTO(
                tool_call_id=r.get("tool_call_id", ""),
                tool_name=r.get("tool_name", ""),
                output=r.get("output", ""),
                success=r.get("success", True),
            )
            for r in state.get("tool_results", [])
        ]

        messages = [
            {"role": _get_message_role(m), "content": _get_message_content(m)}
            for m in state.get("messages", [])
        ]

        return AgentResponseDTO(
            thread_id=thread_id,
            status=status_map.get(state.get("status", ""), AgentStatus.COMPLETED),
            answer=state.get("final_answer", ""),
            confidence=state.get("confidence", 0.0),
            tool_calls=tool_calls,
            tool_results=tool_results,
            requires_approval=state.get("status") == "awaiting_approval",
            pending_action=pending,
            messages=messages,
        )
