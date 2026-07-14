"""LLM usage tracking and cost estimation."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from threading import Lock

from prometheus_client import Counter, Histogram

LLM_REQUESTS = Counter(
    "llm_requests_total",
    "Total LLM requests",
    ["model", "operation", "cached"],
)
LLM_TOKENS = Counter(
    "llm_tokens_total",
    "Total LLM tokens consumed",
    ["model", "token_type"],
)
LLM_COST = Counter(
    "llm_cost_usd_total",
    "Estimated LLM cost in USD",
    ["model"],
)
LLM_LATENCY = Histogram(
    "llm_request_duration_seconds",
    "LLM request latency",
    ["model"],
)

# USD per 1M tokens (approximate OpenAI pricing)
MODEL_PRICING: dict[str, dict[str, float]] = {
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "text-embedding-3-small": {"input": 0.02, "output": 0.0},
    "mock": {"input": 0.0, "output": 0.0},
}


@dataclass
class LLMUsageRecord:
    """Single LLM usage event."""

    model: str
    operation: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    cached: bool = False
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


class LLMUsageTracker:
    """Tracks LLM token usage, cost, and exposes metrics."""

    def __init__(self) -> None:
        self._records: list[LLMUsageRecord] = []
        self._lock = Lock()

    def record(
        self,
        *,
        model: str,
        operation: str,
        input_tokens: int,
        output_tokens: int,
        cached: bool = False,
        latency_seconds: float = 0.0,
    ) -> LLMUsageRecord:
        cost = self._estimate_cost(model, input_tokens, output_tokens)
        record = LLMUsageRecord(
            model=model,
            operation=operation,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost,
            cached=cached,
        )
        with self._lock:
            self._records.append(record)
            if len(self._records) > 1000:
                self._records = self._records[-500:]

        LLM_REQUESTS.labels(model=model, operation=operation, cached=str(cached)).inc()
        LLM_TOKENS.labels(model=model, token_type="input").inc(input_tokens)
        LLM_TOKENS.labels(model=model, token_type="output").inc(output_tokens)
        LLM_COST.labels(model=model).inc(cost)
        if latency_seconds > 0:
            LLM_LATENCY.labels(model=model).observe(latency_seconds)

        return record

    def get_summary(self) -> dict:
        with self._lock:
            records = list(self._records)
        if not records:
            return {
                "total_requests": 0,
                "total_input_tokens": 0,
                "total_output_tokens": 0,
                "total_cost_usd": 0.0,
                "cache_hits": 0,
                "by_model": {},
            }

        by_model: dict[str, dict] = {}
        cache_hits = 0
        for r in records:
            if r.cached:
                cache_hits += 1
            if r.model not in by_model:
                by_model[r.model] = {
                    "requests": 0,
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "cost_usd": 0.0,
                }
            by_model[r.model]["requests"] += 1
            by_model[r.model]["input_tokens"] += r.input_tokens
            by_model[r.model]["output_tokens"] += r.output_tokens
            by_model[r.model]["cost_usd"] += r.cost_usd

        return {
            "total_requests": len(records),
            "total_input_tokens": sum(r.input_tokens for r in records),
            "total_output_tokens": sum(r.output_tokens for r in records),
            "total_cost_usd": round(sum(r.cost_usd for r in records), 6),
            "cache_hits": cache_hits,
            "by_model": by_model,
        }

    @staticmethod
    def _estimate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
        pricing = MODEL_PRICING.get(model, MODEL_PRICING["gpt-4o-mini"])
        input_cost = (input_tokens / 1_000_000) * pricing["input"]
        output_cost = (output_tokens / 1_000_000) * pricing["output"]
        return input_cost + output_cost


def estimate_tokens(text: str) -> int:
    """Rough token estimate (chars / 4)."""
    return max(1, len(text) // 4)
