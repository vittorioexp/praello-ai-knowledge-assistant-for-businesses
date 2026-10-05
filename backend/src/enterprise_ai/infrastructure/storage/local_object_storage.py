"""Local object storage adapter for development and single-node deployments."""

from collections.abc import AsyncIterator
from pathlib import Path

import aiofiles

from enterprise_ai.domain.repositories.object_storage import ObjectStorage


class LocalObjectStorage(ObjectStorage):
    """Store objects as files while preserving the object-storage contract."""

    def __init__(self, base_dir: str) -> None:
        self._base_dir = Path(base_dir)

    async def put(self, key: str, content: AsyncIterator[bytes], *, content_type: str) -> int:
        del content_type
        path = self._path_for(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        total_size = 0
        async with aiofiles.open(path, "wb") as handle:
            async for chunk in content:
                total_size += len(chunk)
                await handle.write(chunk)
        return total_size

    async def open(self, key: str) -> AsyncIterator[bytes]:
        path = self._path_for(key)
        async with aiofiles.open(path, "rb") as handle:
            while chunk := await handle.read(1024 * 1024):
                yield chunk

    async def delete(self, key: str) -> None:
        path = self._path_for(key)
        if path.exists():
            path.unlink()

    def _path_for(self, key: str) -> Path:
        path = (self._base_dir / key).resolve()
        if self._base_dir.resolve() not in path.parents:
            raise ValueError("Object key escapes storage root")
        return path
