"""Tests for LLM usage tracking."""

from enterprise_ai.ai.llm.usage_tracker import LLMUsageTracker, estimate_tokens


def test_estimate_tokens() -> None:
    assert estimate_tokens("hello world") >= 1


def test_tracker_records_usage() -> None:
    tracker = LLMUsageTracker()
    tracker.record(
        model="gpt-4o-mini",
        operation="generate",
        input_tokens=100,
        output_tokens=50,
    )
    summary = tracker.get_summary()
    assert summary["total_requests"] == 1
    assert summary["total_input_tokens"] == 100
    assert summary["total_output_tokens"] == 50
    assert summary["total_cost_usd"] > 0


def test_tracker_records_cache_hits() -> None:
    tracker = LLMUsageTracker()
    tracker.record(
        model="mock",
        operation="generate",
        input_tokens=10,
        output_tokens=10,
        cached=True,
    )
    summary = tracker.get_summary()
    assert summary["cache_hits"] == 1
