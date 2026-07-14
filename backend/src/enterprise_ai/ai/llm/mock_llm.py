"""Mock LLM for testing without API calls."""

import json
import re
from typing import Any

from enterprise_ai.domain.repositories.llm_service import LLMService


class MockLLMService(LLMService):
    """Deterministic LLM responses for tests."""

    async def generate(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.0,
    ) -> str:
        if "enterprise AI agent" in system_prompt.lower() or "tool_name" in system_prompt:
            return self._agent_response(user_prompt)

        if "Rewrite" in user_prompt or "rewrite" in system_prompt.lower():
            query = _extract_after_colon(user_prompt) or user_prompt
            return f"search query about {query}"

        if "alternative search queries" in user_prompt.lower():
            base = _extract_after_colon(user_prompt) or "topic"
            return f"{base}\nrelated policy for {base}\ncompany guidelines {base}"

        if "Context" in user_prompt or "context" in user_prompt.lower():
            return _answer_from_context(user_prompt)

        return "Mock LLM response based on available context."

    async def generate_json(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        schema_hint: str,
    ) -> dict[str, Any]:
        answer = await self.generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )
        return {
            "answer": answer,
            "confidence": 0.85,
            "sources": [],
            "requires_approval": False,
        }

    def _agent_response(self, user_prompt: str) -> str:
        user_msg = _extract_user_message(user_prompt).lower()

        if "recent tool results" in user_prompt.lower():
            return json.dumps({
                "answer": "Based on the tool results, here is the information you requested.",
                "confidence": 0.85,
                "tool_name": None,
                "tool_arguments": {},
                "requires_approval": False,
            })

        if "send email" in user_msg or "email to" in user_msg:
            return json.dumps({
                "answer": "I can send that email for you.",
                "confidence": 0.9,
                "tool_name": "email",
                "tool_arguments": {
                    "to": "team@company.com",
                    "subject": "Notification",
                    "body": "Automated message from agent",
                },
                "requires_approval": True,
            })

        if "slack" in user_msg:
            return json.dumps({
                "answer": "I'll post to Slack.",
                "confidence": 0.9,
                "tool_name": "slack",
                "tool_arguments": {"channel": "general", "message": "Update from agent"},
                "requires_approval": True,
            })

        if "sql" in user_msg or "database" in user_msg or "users table" in user_msg:
            return json.dumps({
                "answer": "Let me query the database.",
                "confidence": 0.8,
                "tool_name": "sql_search",
                "tool_arguments": {"query": "SELECT email, full_name FROM users LIMIT 5"},
                "requires_approval": False,
            })

        if "policy" in user_msg or "remote work" in user_msg or "knowledge" in user_msg:
            query = "remote work policy" if "remote" in user_msg else "company policy"
            return json.dumps({
                "answer": "Let me search the knowledge base.",
                "confidence": 0.8,
                "tool_name": "knowledge_search",
                "tool_arguments": {"query": query},
                "requires_approval": False,
            })

        return json.dumps({
            "answer": "I can help you with that. What would you like to know?",
            "confidence": 0.7,
            "tool_name": None,
            "tool_arguments": {},
            "requires_approval": False,
        })


def _extract_user_message(user_prompt: str) -> str:
    for line in reversed(user_prompt.splitlines()):
        if line.startswith("User:"):
            return line[5:].strip()
    return user_prompt


def _extract_after_colon(text: str) -> str:
    if ":" in text:
        return text.split(":", 1)[1].strip().rstrip(".")
    return ""


def _answer_from_context(user_prompt: str) -> str:
    """Extract a simple answer from context for testing."""
    context_match = re.search(r"Context:\s*(.+?)(?:\n\nQuestion:|$)", user_prompt, re.DOTALL)
    if not context_match:
        return "I don't have enough information to answer that."

    context = context_match.group(1)
    question_match = re.search(r"Question:\s*(.+)", user_prompt, re.DOTALL)
    question = question_match.group(1).strip().lower() if question_match else ""

    if "remote" in question:
        for line in context.splitlines():
            if "remote" in line.lower():
                return line.strip()

    sentences = [s.strip() for s in context.split(".") if s.strip()]
    if sentences:
        return sentences[0] + "."

    return "I don't have enough information to answer that."
