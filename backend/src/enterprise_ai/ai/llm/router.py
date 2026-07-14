"""Model routing for LLM requests."""

from enterprise_ai.infrastructure.config.settings import Settings


class ModelRouter:
    """Routes requests to appropriate models based on complexity."""

    def __init__(self, settings: Settings) -> None:
        self._default = settings.openai_model
        self._fallback = settings.openai_fallback_model
        self._complex = settings.openai_complex_model

    def select_model(self, *, operation: str, prompt_length: int) -> str:
        """Select model based on operation type and prompt size."""
        if operation in ("embedding", "rewrite", "multi_query"):
            return self._default
        if prompt_length > 4000 or operation == "agent":
            return self._complex
        return self._default

    @property
    def fallback_model(self) -> str:
        return self._fallback
