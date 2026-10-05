"""Durable Redis Streams queue for document ingestion jobs."""

from uuid import UUID

from redis.asyncio import Redis
from redis.exceptions import ResponseError


class IngestionQueue:
    """Enqueue and consume ingestion jobs with consumer-group semantics."""

    stream_name = "enterprise_ai:ingestion"
    group_name = "ingestion-workers"
    dead_letter_stream = "enterprise_ai:ingestion:dead-letter"

    def __init__(self, client: Redis) -> None:
        self._client = client

    async def ensure_group(self) -> None:
        try:
            await self._client.xgroup_create(
                self.stream_name,
                self.group_name,
                id="0",
                mkstream=True,
            )
        except ResponseError as exc:
            if "BUSYGROUP" not in str(exc):
                raise

    async def enqueue(self, document_id: UUID) -> str:
        message_id = await self._client.xadd(
            self.stream_name,
            {"document_id": str(document_id), "attempts": "0"},
        )
        return str(message_id)

    async def retry_or_dead_letter(
        self,
        message_id: str,
        fields: dict[str, str],
        *,
        max_attempts: int,
        error: str,
    ) -> bool:
        attempts = int(fields.get("attempts", "0")) + 1
        await self._client.xack(self.stream_name, self.group_name, message_id)
        if attempts >= max_attempts:
            await self._client.xadd(
                self.dead_letter_stream,
                {**fields, "attempts": str(attempts), "error": error},
            )
            return False
        await self._client.xadd(
            self.stream_name,
            {**fields, "attempts": str(attempts)},
        )
        return True

    async def replay_dead_letters(self, *, count: int = 100) -> int:
        records = await self._client.xread(
            {self.dead_letter_stream: "0-0"},
            count=count,
            block=1,
        )
        replayed = 0
        for _, messages in records or []:
            for message_id, fields in messages:
                await self._client.xadd(
                    self.stream_name,
                    {key: value for key, value in fields.items() if key != "error"} | {"attempts": "0"},
                )
                await self._client.xdel(self.dead_letter_stream, message_id)
                replayed += 1
        return replayed

    async def read(self, consumer_name: str, *, count: int = 1) -> list[tuple[str, dict[str, str]]]:
        reclaimed = await self._client.xautoclaim(
            self.stream_name,
            self.group_name,
            consumer_name,
            min_idle_time=60_000,
            start_id="0-0",
            count=count,
        )
        if reclaimed[1]:
            return [(message_id, fields) for message_id, fields, *_ in reclaimed[1]]
        records = await self._client.xreadgroup(
            self.group_name,
            consumer_name,
            {self.stream_name: ">"},
            count=count,
            block=5000,
        )
        if not records:
            return []
        return [(message_id, fields) for _, messages in records for message_id, fields in messages]

    async def acknowledge(self, message_id: str) -> None:
        await self._client.xack(self.stream_name, self.group_name, message_id)
