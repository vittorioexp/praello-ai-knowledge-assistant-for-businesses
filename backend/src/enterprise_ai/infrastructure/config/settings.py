"""Application configuration."""

from functools import lru_cache
from typing import Literal

from pydantic import Field, PostgresDsn, RedisDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Centralized application settings loaded from environment."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = "Praello AI Knowledge Assistant for Businesses"
    app_env: Literal["development", "staging", "production", "test"] = "development"
    app_debug: bool = False
    app_secret_key: str = Field(min_length=32)
    api_v1_prefix: str = "/api/v1"
    cors_origins: str = "http://localhost:3000"

    # Database
    database_url: PostgresDsn | str = Field(
        default="postgresql+asyncpg://enterprise_ai:enterprise_ai_secret@localhost:5432/enterprise_ai"
    )

    # Redis
    redis_url: RedisDsn | str = "redis://localhost:6379/0"
    rate_limit_requests: int = 120
    rate_limit_window_seconds: int = 60

    # Qdrant
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    qdrant_collection: str = "enterprise_knowledge"

    # OpenAI
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    openai_embedding_model: str = "text-embedding-3-small"
    openai_fallback_model: str = "gpt-4o-mini"

    # LangSmith
    langchain_tracing_v2: bool = False
    langchain_api_key: str = ""
    langchain_project: str = "praello-ai-knowledge-assistant"

    # JWT
    jwt_secret_key: str = Field(min_length=32)
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 7

    # Observability
    otel_enabled: bool = False
    otel_service_name: str = "praello-ai-knowledge-assistant"
    prometheus_enabled: bool = True

    # Uploads
    upload_max_size_mb: int = 5120
    upload_dir: str = "/app/uploads"
    storage_backend: Literal["local", "s3"] = "local"
    s3_bucket: str = "enterprise-ai-documents"
    s3_region: str = ""
    s3_endpoint_url: str = ""
    s3_access_key_id: str = ""
    s3_secret_access_key: str = ""

    # Connector OAuth
    google_oauth_client_id: str = ""
    google_oauth_client_secret: str = ""
    google_oauth_redirect_uri: str = ""
    microsoft_oauth_client_id: str = ""
    microsoft_oauth_client_secret: str = ""
    microsoft_oauth_redirect_uri: str = ""
    oidc_issuer_url: str = ""
    oidc_client_id: str = ""
    oidc_client_secret: str = ""
    oidc_redirect_uri: str = ""
    saml_enabled: bool = False
    saml_idp_entity_id: str = ""
    saml_idp_sso_url: str = ""
    saml_idp_x509_cert: str = ""
    saml_sp_entity_id: str = "praello-ai"
    saml_acs_url: str = ""
    scim_bearer_token: str = ""
    scim_organization_id: str = ""

    # Chunking
    chunk_size: int = 1000
    chunk_overlap: int = 200
    embedding_batch_size: int = 128
    vector_upsert_batch_size: int = 256
    max_ingestion_attempts: int = 5

    # RAG
    rag_top_k: int = 10
    rag_rerank_top_k: int = 5
    rag_rrf_k: int = 60
    rag_hybrid_dense_weight: float = 0.5
    rag_multi_query_count: int = 3
    rag_max_context_chars: int = 8000
    rag_confidence_threshold: float = 0.3

    # Agent
    agent_max_retries: int = 3
    agent_max_tool_calls: int = 5
    agent_checkpoint_backend: Literal["memory", "redis"] = "memory"

    # LLMOps
    llm_cache_enabled: bool = True
    llm_cache_ttl_seconds: int = 3600
    llm_max_retries: int = 2
    openai_complex_model: str = "gpt-4o"

    @field_validator("database_url", mode="before")
    @classmethod
    def validate_database_url(cls, value: str) -> str:
        if isinstance(value, str) and value.startswith("postgresql://"):
            return value.replace("postgresql://", "postgresql+asyncpg://", 1)
        return value

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def is_test(self) -> bool:
        return self.app_env == "test"


@lru_cache
def get_settings() -> Settings:
    """Return cached settings singleton."""
    return Settings()  # type: ignore[call-arg]
