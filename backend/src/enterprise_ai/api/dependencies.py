"""FastAPI dependency injection."""

from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from enterprise_ai.application.services.agent_service import AgentService
from enterprise_ai.application.services.auth_service import AuthService
from enterprise_ai.application.services.document_service import DocumentService
from enterprise_ai.application.services.health_service import HealthService
from enterprise_ai.application.services.ingestion_service import IngestionService
from enterprise_ai.application.services.rag_service import RAGService
from enterprise_ai.ai.guardrails.prompt_injection import PromptInjectionGuard
from enterprise_ai.ai.ingestion.chunking import ChunkingService
from enterprise_ai.ai.rag.confidence import ConfidenceScorer
from enterprise_ai.ai.rag.context_compressor import ContextCompressor
from enterprise_ai.ai.rag.hybrid_retriever import HybridRetriever
from enterprise_ai.ai.rag.query_rewriter import MultiQueryExpander, QueryRewriter
from enterprise_ai.ai.rag.reranker import RerankerService
from enterprise_ai.domain.entities.user import User
from enterprise_ai.domain.exceptions import AuthenticationError
from enterprise_ai.domain.repositories.embedding_service import EmbeddingService
from enterprise_ai.domain.repositories.llm_service import LLMService
from enterprise_ai.domain.repositories.vector_store import VectorStore
from enterprise_ai.infrastructure.cache.redis_client import RedisClient
from enterprise_ai.infrastructure.config.settings import Settings, get_settings
from enterprise_ai.infrastructure.database.session import Database
from enterprise_ai.infrastructure.repositories.document_repository import SQLAlchemyDocumentRepository
from enterprise_ai.infrastructure.repositories.user_repository import SQLAlchemyUserRepository
from enterprise_ai.infrastructure.security.jwt import JWTService
from enterprise_ai.infrastructure.storage.file_storage import FileStorageService

security = HTTPBearer(auto_error=False)


def get_app_settings() -> Settings:
    return get_settings()


def get_database(request: Request) -> Database:
    return request.app.state.database


def get_redis(request: Request) -> RedisClient:
    return request.app.state.redis


async def get_db_session(
    database: Annotated[Database, Depends(get_database)],
) -> AsyncGenerator[AsyncSession, None]:
    async for session in database.session():
        yield session


def get_jwt_service(
    settings: Annotated[Settings, Depends(get_app_settings)],
) -> JWTService:
    return JWTService(settings)


def get_auth_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    jwt_service: Annotated[JWTService, Depends(get_jwt_service)],
    settings: Annotated[Settings, Depends(get_app_settings)],
) -> AuthService:
    return AuthService(SQLAlchemyUserRepository(session), jwt_service, settings)


def get_health_service(
    settings: Annotated[Settings, Depends(get_app_settings)],
    database: Annotated[Database, Depends(get_database)],
    redis: Annotated[RedisClient, Depends(get_redis)],
) -> HealthService:
    return HealthService(settings, database, redis)


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    jwt_service: Annotated[JWTService, Depends(get_jwt_service)],
) -> User:
    """Extract and validate the current user from JWT bearer token."""
    if credentials is None:
        raise AuthenticationError("Authentication required")
    payload = jwt_service.decode_token(credentials.credentials)
    return await auth_service.get_current_user(payload.sub)


def get_file_storage(
    settings: Annotated[Settings, Depends(get_app_settings)],
) -> FileStorageService:
    return FileStorageService(settings)


def get_vector_store(
    request: Request,
) -> VectorStore:
    return request.app.state.vector_store


def get_embedding_service(
    request: Request,
) -> EmbeddingService:
    return request.app.state.embedding_service


def get_chunking_service(
    settings: Annotated[Settings, Depends(get_app_settings)],
) -> ChunkingService:
    return ChunkingService(settings)


def get_ingestion_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    embedding_service: Annotated[EmbeddingService, Depends(get_embedding_service)],
    vector_store: Annotated[VectorStore, Depends(get_vector_store)],
    chunking_service: Annotated[ChunkingService, Depends(get_chunking_service)],
) -> IngestionService:
    return IngestionService(
        SQLAlchemyDocumentRepository(session),
        embedding_service,
        vector_store,
        chunking_service,
    )


def get_document_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    file_storage: Annotated[FileStorageService, Depends(get_file_storage)],
    ingestion_service: Annotated[IngestionService, Depends(get_ingestion_service)],
    vector_store: Annotated[VectorStore, Depends(get_vector_store)],
) -> DocumentService:
    return DocumentService(
        SQLAlchemyDocumentRepository(session),
        file_storage,
        ingestion_service,
        vector_store,
    )


def get_llm_service(request: Request) -> LLMService:
    return request.app.state.llm_service


def get_rag_service(
    settings: Annotated[Settings, Depends(get_app_settings)],
    vector_store: Annotated[VectorStore, Depends(get_vector_store)],
    embedding_service: Annotated[EmbeddingService, Depends(get_embedding_service)],
    llm_service: Annotated[LLMService, Depends(get_llm_service)],
) -> RAGService:
    return RAGService(
        hybrid_retriever=HybridRetriever(vector_store, embedding_service, settings),
        query_rewriter=QueryRewriter(llm_service),
        multi_query=MultiQueryExpander(llm_service, settings),
        reranker=RerankerService(),
        context_compressor=ContextCompressor(settings),
        confidence_scorer=ConfidenceScorer(settings),
        llm_service=llm_service,
        injection_guard=PromptInjectionGuard(),
        settings=settings,
    )


def get_agent_service(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    llm_service: Annotated[LLMService, Depends(get_llm_service)],
    rag_service: Annotated[RAGService, Depends(get_rag_service)],
    settings: Annotated[Settings, Depends(get_app_settings)],
) -> AgentService:
    return AgentService(
        llm_service,
        rag_service,
        session,
        settings,
        checkpointer=request.app.state.agent_checkpointer,
    )
