"""LangGraph agent state definition."""

from typing import Annotated, Any, TypedDict

from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    """State passed between agent graph nodes."""

    messages: Annotated[list[dict[str, Any]], add_messages]
    user_id: str
    thread_id: str
    retry_count: int
    tool_call_count: int
    pending_tool: dict[str, Any] | None
    approval_granted: bool
    tool_results: list[dict[str, Any]]
    final_answer: str
    confidence: float
    status: str
    blocked: bool
    error: str | None
