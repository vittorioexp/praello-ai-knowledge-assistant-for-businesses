"""FastAPI application factory."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from enterprise_ai import __version__
from enterprise_ai.api.middleware.exception_handlers import register_exception_handlers
from enterprise_ai.api.middleware.logging import RequestLoggingMiddleware
from enterprise_ai.api.routes import api_v1_router
from enterprise_ai.domain.repositories.embedding_service import EmbeddingService
from enterprise_ai.domain.repositories.vector_store import VectorStore
from enterprise_ai.infrastructure.cache.redis_client import RedisClient
from enterprise_ai.infrastructure.config.settings import Settings, get_settings
from enterprise_ai.infrastructure.database.session import Database
from langgraph.checkpoint.memory import MemorySaver

from enterprise_ai.infrastructure.factories.ai_factory import (
    create_embedding_service,
    create_llm_service,
    create_llm_tracker,
    create_vector_store,
)
from enterprise_ai.infrastructure.logging.setup import configure_logging, get_logger
from enterprise_ai.infrastructure.observability.langsmith import setup_langsmith
from enterprise_ai.infrastructure.observability.telemetry import instrument_fastapi, setup_telemetry

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application startup and shutdown."""
    settings: Settings = app.state.settings
    logger.info("application_starting", version=__version__, env=settings.app_env)

    embedding_service: EmbeddingService = app.state.embedding_service
    vector_store: VectorStore = app.state.vector_store
    try:
        await vector_store.ensure_collection(embedding_service.vector_size)
    except Exception as exc:
        logger.warning("vector_store_init_skipped", error=str(exc))

    yield

    await app.state.database.dispose()
    await app.state.redis.close()
    if hasattr(app.state.vector_store, "_client"):
        await app.state.vector_store._client.close()  # noqa: SLF001
    logger.info("application_shutdown")


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = settings or get_settings()
    configure_logging(debug=settings.app_debug)
    setup_telemetry(settings)
    setup_langsmith(settings)

    app = FastAPI(
        title=settings.app_name,
        version=__version__,
        description="Praello AI Knowledge Assistant for Businesses API",
        docs_url=f"{settings.api_v1_prefix}/docs",
        redoc_url=f"{settings.api_v1_prefix}/redoc",
        openapi_url=f"{settings.api_v1_prefix}/openapi.json",
        lifespan=lifespan,
    )

    app.state.settings = settings
    app.state.database = Database(settings)
    app.state.redis = RedisClient(settings)
    app.state.embedding_service = create_embedding_service(settings)
    app.state.vector_store = create_vector_store(settings)
    app.state.llm_tracker = create_llm_tracker()
    app.state.llm_service = create_llm_service(
        settings, redis=app.state.redis, tracker=app.state.llm_tracker
    )
    app.state.agent_checkpointer = MemorySaver()

    instrument_fastapi(app)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(RequestLoggingMiddleware)

    register_exception_handlers(app)
    app.include_router(api_v1_router, prefix=settings.api_v1_prefix)

    @app.get("/", include_in_schema=False)
    async def root() -> dict[str, str]:
        return {
            "name": settings.app_name,
            "version": __version__,
            "docs": f"{settings.api_v1_prefix}/docs",
        }

    return app
