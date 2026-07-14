"""Read-only SQL search tool."""

import re

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from enterprise_ai.ai.tools.base import AgentTool
from enterprise_ai.domain.value_objects.agent import ToolRiskLevel

ALLOWED_TABLES = {"users", "documents"}
FORBIDDEN_KEYWORDS = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|TRUNCATE|CREATE|GRANT|REVOKE)\b",
    re.IGNORECASE,
)


class SQLSearchTool(AgentTool):
    """Execute read-only SQL queries against approved tables."""

    name = "sql_search"
    description = (
        "Run read-only SELECT queries on users and documents tables. "
        "Example: SELECT id, email FROM users LIMIT 5"
    )
    risk_level = ToolRiskLevel.MEDIUM
    requires_approval = False

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def execute(self, *, query: str, **kwargs) -> str:
        normalized = query.strip()
        if not normalized.upper().startswith("SELECT"):
            return "Error: only SELECT queries are allowed"
        if FORBIDDEN_KEYWORDS.search(normalized):
            return "Error: query contains forbidden keywords"
        for table in re.findall(r"\bFROM\s+(\w+)", normalized, re.IGNORECASE):
            if table.lower() not in ALLOWED_TABLES:
                return f"Error: table '{table}' is not allowed"

        try:
            result = await self._session.execute(text(normalized))
            rows = result.fetchmany(20)
            if not rows:
                return "No results found"
            return "\n".join(str(dict(row._mapping)) for row in rows)
        except Exception as exc:
            return f"SQL error: {exc}"
