"""Knowledge base query API routes."""

from typing import Annotated

from fastapi import APIRouter, Depends

from enterprise_ai.api.dependencies import get_rag_service
from enterprise_ai.api.middleware.rbac import require_permission
from enterprise_ai.application.dto.rag import RAGQueryRequestDTO, RAGQueryResponseDTO
from enterprise_ai.application.services.rag_service import RAGService
from enterprise_ai.domain.entities.user import User
from enterprise_ai.domain.value_objects.role import Permission

router = APIRouter(prefix="/knowledge", tags=["RAG"])


@router.post("/query", response_model=RAGQueryResponseDTO)
async def query_knowledge(
    request: RAGQueryRequestDTO,
    rag_service: Annotated[RAGService, Depends(get_rag_service)],
    current_user: Annotated[User, Depends(require_permission(Permission.KNOWLEDGE_QUERY.value))],
) -> RAGQueryResponseDTO:
    """Query the knowledge base using hybrid RAG with citations."""
    return await rag_service.query(request, current_user)
