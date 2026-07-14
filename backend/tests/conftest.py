"""Test configuration and fixtures."""

import os
from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from enterprise_ai.domain.value_objects.role import Role
from enterprise_ai.infrastructure.config.settings import Settings, get_settings
from enterprise_ai.infrastructure.database.models.document import DocumentModel  # noqa: F401
from enterprise_ai.infrastructure.database.models.user import UserModel  # noqa: F401
from enterprise_ai.infrastructure.database.session import Base, Database
from enterprise_ai.main import create_app

# Test environment variables (set before any settings import)
os.environ["APP_ENV"] = "test"
os.environ["APP_SECRET_KEY"] = "test-secret-key-minimum-32-chars-long"
os.environ["JWT_SECRET_KEY"] = "test-jwt-secret-key-min-32-chars"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["REDIS_URL"] = "redis://localhost:6379/0"


@pytest.fixture(autouse=True)
def _clear_settings_cache() -> None:
    get_settings.cache_clear()


@pytest.fixture
def upload_dir(tmp_path):
    return str(tmp_path / "uploads")


@pytest.fixture
def test_settings(upload_dir) -> Settings:
    """Provide test settings."""
    return Settings(
        app_env="test",
        app_debug=True,
        app_secret_key="test-secret-key-minimum-32-chars-long",
        jwt_secret_key="test-jwt-secret-key-min-32-chars",
        database_url="sqlite+aiosqlite:///:memory:",
        redis_url="redis://localhost:6379/0",
        upload_dir=upload_dir,
        chunk_size=200,
        chunk_overlap=50,
    )


@pytest.fixture
async def db_engine(test_settings: Settings):
    """Create in-memory SQLite engine for tests."""
    engine = create_async_engine(str(test_settings.database_url), echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture
async def db_session(db_engine) -> AsyncGenerator[AsyncSession, None]:
    """Provide a database session."""
    session_factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session


@pytest.fixture
def mock_redis() -> MagicMock:
    """Mock Redis client for tests without Redis."""
    mock = MagicMock()
    mock.health_check = AsyncMock(return_value=True)
    mock.close = AsyncMock()
    return mock


@pytest.fixture
async def app(test_settings: Settings, mock_redis: MagicMock):
    """Create test FastAPI application."""
    application = create_app(test_settings)
    application.state.redis = mock_redis

    # Create tables for in-memory SQLite
    async with application.state.database.engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield application
    await application.state.database.dispose()


@pytest.fixture
async def client(app) -> AsyncGenerator[AsyncClient, None]:
    """Async HTTP test client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def database(test_settings: Settings) -> Database:
    """Standalone database instance for unit tests."""
    return Database(test_settings)


async def _auth_token(
    client: AsyncClient,
    app,
    email: str,
    role: Role | None = None,
) -> str:
    """Register, optionally upgrade role, login, and return access token."""
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "securepass123",
            "full_name": "Test User",
        },
    )
    if role and role != Role.VIEWER:
        from sqlalchemy import update

        from enterprise_ai.infrastructure.database.models.user import UserModel

        async with app.state.database.engine.begin() as conn:
            await conn.execute(
                update(UserModel).where(UserModel.email == email).values(role=role.value)
            )

    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "securepass123"},
    )
    return login_resp.json()["access_token"]


@pytest.fixture
async def contributor_token(client: AsyncClient, app) -> str:
    return await _auth_token(client, app, "contributor@company.com", Role.CONTRIBUTOR)


@pytest.fixture
async def analyst_token(client: AsyncClient, app) -> str:
    return await _auth_token(client, app, "analyst@company.com", Role.ANALYST)


@pytest.fixture
async def admin_token(client: AsyncClient, app) -> str:
    return await _auth_token(client, app, "admin@company.com", Role.ADMIN)
