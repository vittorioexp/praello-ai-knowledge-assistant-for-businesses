"""LangGraph agent graph builder."""

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from enterprise_ai.ai.agents.nodes import (
    AgentNodes,
    route_after_agent,
    route_after_guardrails,
    route_after_tools,
    route_entry,
)
from enterprise_ai.ai.agents.state import AgentState
from enterprise_ai.ai.tools.base import ToolRegistry
from enterprise_ai.domain.repositories.llm_service import LLMService
from enterprise_ai.infrastructure.config.settings import Settings


def build_agent_graph(
    llm_service: LLMService,
    tool_registry: ToolRegistry,
    settings: Settings,
    checkpointer: MemorySaver | None = None,
):
    """Build and compile the enterprise agent graph."""
    nodes = AgentNodes(llm_service, tool_registry, settings)

    graph = StateGraph(AgentState)

    graph.add_node("router", lambda state: state)
    graph.add_node("guardrails", nodes.guardrails)
    graph.add_node("agent", nodes.agent)
    graph.add_node("execute_tools", nodes.execute_tools)
    graph.add_node("format_output", nodes.format_output)

    graph.set_entry_point("router")

    graph.add_conditional_edges("router", route_entry, {
        "guardrails": "guardrails",
        "execute_tools": "execute_tools",
    })
    graph.add_conditional_edges("guardrails", route_after_guardrails, {
        "agent": "agent",
        "format_output": "format_output",
    })
    graph.add_conditional_edges("agent", route_after_agent, {
        "execute_tools": "execute_tools",
        "agent": "agent",
        "format_output": "format_output",
    })
    graph.add_conditional_edges("execute_tools", route_after_tools, {
        "agent": "agent",
        "format_output": "format_output",
    })
    graph.add_edge("format_output", END)

    return graph.compile(checkpointer=checkpointer or MemorySaver())
