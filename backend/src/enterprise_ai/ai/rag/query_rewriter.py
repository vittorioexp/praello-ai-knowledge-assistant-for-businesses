"""Query rewriting and multi-query expansion."""

from enterprise_ai.domain.repositories.llm_service import LLMService
from enterprise_ai.infrastructure.config.settings import Settings
from enterprise_ai.infrastructure.logging.setup import get_logger

logger = get_logger(__name__)

REWRITE_SYSTEM = """You rewrite user queries for enterprise knowledge base search.
Return only the rewritten query, no explanation. Keep it concise and search-oriented."""

MULTI_QUERY_SYSTEM = """Generate alternative search queries for a knowledge base.
Return one query per line, no numbering or bullets."""


class QueryRewriter:
    """Rewrites queries for improved retrieval."""

    def __init__(self, llm_service: LLMService) -> None:
        self._llm = llm_service

    async def rewrite(self, query: str) -> str:
        rewritten = await self._llm.generate(
            system_prompt=REWRITE_SYSTEM,
            user_prompt=f"Rewrite this query for document search: {query}",
            temperature=0.0,
        )
        result = rewritten.strip() or query
        logger.info("query_rewritten", original=query, rewritten=result)
        return result


class MultiQueryExpander:
    """Generates multiple query variants for broader recall."""

    def __init__(self, llm_service: LLMService, settings: Settings) -> None:
        self._llm = llm_service
        self._count = settings.rag_multi_query_count

    async def expand(self, query: str) -> list[str]:
        response = await self._llm.generate(
            system_prompt=MULTI_QUERY_SYSTEM,
            user_prompt=(
                f"Generate {self._count} alternative search queries for: {query}"
            ),
            temperature=0.3,
        )
        variants = [line.strip() for line in response.splitlines() if line.strip()]
        unique = list(dict.fromkeys([query, *variants]))
        logger.info("multi_query_expanded", count=len(unique))
        return unique[: self._count + 1]
