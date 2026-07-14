"""Agent conversation domain entity."""

from uuid import UUID

from pydantic import Field

from enterprise_ai.domain.entities.base import Entity
from enterprise_ai.domain.value_objects.agent import ConversationStatus


class Conversation(Entity):
    """Multi-turn agent conversation with checkpointed state."""

    user_id: UUID
    title: str = "New Conversation"
    status: ConversationStatus = ConversationStatus.ACTIVE
    thread_id: str = Field(description="LangGraph checkpoint thread ID")
    message_count: int = 0

    def increment_messages(self) -> None:
        self.message_count += 1
        self.touch()

    def mark_awaiting_approval(self) -> None:
        self.status = ConversationStatus.AWAITING_APPROVAL
        self.touch()

    def mark_completed(self) -> None:
        self.status = ConversationStatus.COMPLETED
        self.touch()

    def mark_failed(self) -> None:
        self.status = ConversationStatus.FAILED
        self.touch()

    def reactivate(self) -> None:
        self.status = ConversationStatus.ACTIVE
        self.touch()
