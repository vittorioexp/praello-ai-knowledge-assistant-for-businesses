"""Tests for bounded ingestion retries."""

import pytest

from enterprise_ai.infrastructure.queue.ingestion_queue import IngestionQueue


class FakeRedis:
    def __init__(self) -> None:
        self.acked: list[tuple[str, str, str]] = []
        self.added: list[tuple[str, dict[str, str]]] = []

    async def xack(self, stream: str, group: str, message_id: str) -> None:
        self.acked.append((stream, group, message_id))

    async def xadd(self, stream: str, fields: dict[str, str]) -> str:
        self.added.append((stream, fields))
        return "2-0"


@pytest.mark.asyncio
async def test_failed_job_is_requeued_with_incremented_attempts() -> None:
    redis = FakeRedis()
    queue = IngestionQueue(redis)  # type: ignore[arg-type]

    should_retry = await queue.retry_or_dead_letter(
        "1-0",
        {"document_id": "doc-1", "attempts": "1"},
        max_attempts=3,
        error="temporary",
    )

    assert should_retry is True
    assert redis.acked == [(queue.stream_name, queue.group_name, "1-0")]
    assert redis.added == [(queue.stream_name, {"document_id": "doc-1", "attempts": "2"})]


@pytest.mark.asyncio
async def test_failed_job_is_sent_to_dead_letter_at_limit() -> None:
    redis = FakeRedis()
    queue = IngestionQueue(redis)  # type: ignore[arg-type]

    should_retry = await queue.retry_or_dead_letter(
        "1-0",
        {"document_id": "doc-1", "attempts": "2"},
        max_attempts=3,
        error="permanent",
    )

    assert should_retry is False
    assert redis.added == [
        (
            queue.dead_letter_stream,
            {"document_id": "doc-1", "attempts": "3", "error": "permanent"},
        )
    ]
