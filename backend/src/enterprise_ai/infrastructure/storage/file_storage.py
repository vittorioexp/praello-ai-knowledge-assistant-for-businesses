"""Local filesystem storage for uploaded documents."""

import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from pathlib import Path

import aiofiles

from enterprise_ai.domain.exceptions import ValidationError
from enterprise_ai.infrastructure.config.settings import Settings
from enterprise_ai.infrastructure.logging.setup import get_logger

logger = get_logger(__name__)


class FileStorageService:
    """Stores uploaded files on the local filesystem."""

    def __init__(self, settings: Settings) -> None:
        self._base_dir = Path(settings.upload_dir)
        self._max_size = settings.upload_max_size_mb * 1024 * 1024

    def ensure_upload_dir(self) -> None:
        self._base_dir.mkdir(parents=True, exist_ok=True)

    async def save(self, *, filename: str, content: bytes) -> str:
        """Save file content and return the stored path."""
        if len(content) > self._max_size:
            raise ValidationError(
                f"File exceeds maximum size of {self._max_size // (1024 * 1024)}MB"
            )
        self.ensure_upload_dir()
        unique_name = f"{uuid.uuid4().hex}_{filename}"
        file_path = self._base_dir / unique_name
        async with aiofiles.open(file_path, "wb") as f:
            await f.write(content)
        logger.info("file_saved", path=str(file_path), size=len(content))
        return str(file_path)

    async def save_stream(
        self,
        *,
        filename: str,
        read_chunk: Callable[[int], Awaitable[bytes]],
    ) -> tuple[str, int]:
        """Persist an upload incrementally and return its path and byte count."""
        self.ensure_upload_dir()
        unique_name = f"{uuid.uuid4().hex}_{filename}"
        file_path = self._base_dir / unique_name
        total_size = 0
        try:
            async with aiofiles.open(file_path, "wb") as file_handle:
                while chunk := await read_chunk(1024 * 1024):
                    total_size += len(chunk)
                    if total_size > self._max_size:
                        raise ValidationError(
                            f"File exceeds maximum size of {self._max_size // (1024 * 1024)}MB"
                        )
                    await file_handle.write(chunk)
        except Exception:
            if file_path.exists():
                file_path.unlink()
            raise
        logger.info("file_saved", path=str(file_path), size=total_size)
        return str(file_path), total_size

    async def save_iterator(self, *, filename: str, content: AsyncIterator[bytes]) -> tuple[str, int]:
        """Persist an async byte iterator without buffering it in memory."""
        iterator = content.__aiter__()

        async def read_chunk(_size: int) -> bytes:
            try:
                return await iterator.__anext__()
            except StopAsyncIteration:
                return b""

        return await self.save_stream(filename=filename, read_chunk=read_chunk)

    async def delete(self, file_path: str) -> None:
        """Remove a stored file if it exists."""
        path = Path(file_path)
        if path.exists():
            path.unlink()
            logger.info("file_deleted", path=file_path)

    def read_bytes(self, file_path: str) -> bytes:
        """Read file content synchronously (for parsers)."""
        return Path(file_path).read_bytes()
