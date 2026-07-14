"""Local filesystem storage for uploaded documents."""

import uuid
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

    async def delete(self, file_path: str) -> None:
        """Remove a stored file if it exists."""
        path = Path(file_path)
        if path.exists():
            path.unlink()
            logger.info("file_deleted", path=file_path)

    def read_bytes(self, file_path: str) -> bytes:
        """Read file content synchronously (for parsers)."""
        return Path(file_path).read_bytes()
