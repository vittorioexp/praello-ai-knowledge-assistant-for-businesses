"""Materialize remote streams as temporary files for existing parsers."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from tempfile import mkstemp
from typing import AsyncIterator as AsyncIteratorType
import os


@asynccontextmanager
async def materialize_stream(
    content: AsyncIterator[bytes],
    *,
    suffix: str = "",
) -> AsyncIteratorType[Path]:
    """Write a remote stream to disk and remove it after processing."""
    descriptor, filename = mkstemp(prefix="enterprise-ai-", suffix=suffix)
    path = Path(filename)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            async for chunk in content:
                handle.write(chunk)
        yield path
    finally:
        path.unlink(missing_ok=True)
