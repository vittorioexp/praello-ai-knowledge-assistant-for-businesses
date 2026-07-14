"""LangSmith tracing configuration."""

import os

from enterprise_ai.infrastructure.config.settings import Settings
from enterprise_ai.infrastructure.logging.setup import get_logger

logger = get_logger(__name__)


def setup_langsmith(settings: Settings) -> None:
    """Configure LangSmith environment variables for tracing."""
    if not settings.langchain_tracing_v2 or not settings.langchain_api_key:
        os.environ.setdefault("LANGCHAIN_TRACING_V2", "false")
        return

    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_API_KEY"] = settings.langchain_api_key
    os.environ["LANGCHAIN_PROJECT"] = settings.langchain_project
    logger.info("langsmith_configured", project=settings.langchain_project)
