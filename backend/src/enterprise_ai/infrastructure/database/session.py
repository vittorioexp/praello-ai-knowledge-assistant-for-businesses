"""SQLAlchemy database infrastructure."""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from enterprise_ai.infrastructure.config.settings import Settings


class Base(DeclarativeBase):
    """SQLAlchemy declarative base."""


class Database:
    """Database connection manager."""

    def __init__(self, settings: Settings) -> None:
        engine_kwargs: dict = {
            "echo": settings.app_debug and not settings.is_test,
            "pool_pre_ping": True,
        }
        if "sqlite" not in str(settings.database_url):
            engine_kwargs["pool_size"] = 10
            engine_kwargs["max_overflow"] = 20

        self._engine: AsyncEngine = create_async_engine(
            str(settings.database_url),
            **engine_kwargs,
        )
        self._session_factory = async_sessionmaker(
            self._engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )

    @property
    def engine(self) -> AsyncEngine:
        return self._engine

    async def session(self) -> AsyncGenerator[AsyncSession, None]:
        """Yield a database session."""
        async with self._session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    async def health_check(self) -> bool:
        """Verify database connectivity."""
        from sqlalchemy import text

        try:
            async with self._engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            return True
        except Exception:
            return False

    async def dispose(self) -> None:
        """Close all connections."""
        await self._engine.dispose()
