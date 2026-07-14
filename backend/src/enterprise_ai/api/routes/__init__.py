"""API v1 router aggregation."""

from fastapi import APIRouter

from enterprise_ai.api.routes import agent, auth, documents, health, knowledge, llm_ops, metrics

api_v1_router = APIRouter()
api_v1_router.include_router(health.router)
api_v1_router.include_router(metrics.router)
api_v1_router.include_router(auth.router)
api_v1_router.include_router(documents.router)
api_v1_router.include_router(knowledge.router)
api_v1_router.include_router(agent.router)
api_v1_router.include_router(llm_ops.router)
