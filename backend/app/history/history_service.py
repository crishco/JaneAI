"""Conversation history persistence service."""

import logging
import uuid
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select

from app.database.database import get_db_session
from app.database.models import Conversation, Message

logger = logging.getLogger(__name__)


class HistoryServiceError(Exception):
    """Raised when a history operation fails."""


@dataclass(frozen=True)
class HistoryMessage:
    """A stored conversation message."""

    id: int
    conversation_id: str
    role: str
    content: str
    created_at: datetime


class HistoryService:
    """Manages conversation and message persistence in SQLite."""

    def create_conversation(self) -> str:
        """Create a new conversation and return its ID."""
        conversation_id = str(uuid.uuid4())

        with get_db_session() as session:
            conversation = Conversation(id=conversation_id)
            session.add(conversation)

        logger.info("Created conversation %s", conversation_id)
        return conversation_id

    def conversation_exists(self, conversation_id: str) -> bool:
        """Return True if the conversation exists."""
        with get_db_session() as session:
            result = session.scalar(
                select(Conversation.id).where(Conversation.id == conversation_id)
            )
            return result is not None

    def add_message(self, conversation_id: str, role: str, content: str) -> HistoryMessage:
        """Append a message to an existing conversation."""
        normalized_role = role.strip().lower()
        if normalized_role not in {"user", "assistant"}:
            raise HistoryServiceError(f"Invalid message role: {role}")

        normalized_content = content.strip()
        if not normalized_content:
            raise HistoryServiceError("Message content cannot be empty")

        with get_db_session() as session:
            conversation = session.get(Conversation, conversation_id)
            if conversation is None:
                raise HistoryServiceError(f"Conversation not found: {conversation_id}")

            message = Message(
                conversation_id=conversation_id,
                role=normalized_role,
                content=normalized_content,
            )
            session.add(message)
            session.flush()
            session.refresh(message)

            conversation.updated_at = message.created_at
            stored = HistoryMessage(
                id=message.id,
                conversation_id=message.conversation_id,
                role=message.role,
                content=message.content,
                created_at=message.created_at,
            )

        logger.debug(
            "Stored %s message in conversation %s (id=%d)",
            normalized_role,
            conversation_id,
            stored.id,
        )
        return stored

    def get_messages(self, conversation_id: str) -> list[HistoryMessage]:
        """Return all messages for a conversation ordered by timestamp."""
        with get_db_session() as session:
            conversation = session.get(Conversation, conversation_id)
            if conversation is None:
                raise HistoryServiceError(f"Conversation not found: {conversation_id}")

            messages = session.scalars(
                select(Message)
                .where(Message.conversation_id == conversation_id)
                .order_by(Message.created_at.asc())
            ).all()

            return [
                HistoryMessage(
                    id=message.id,
                    conversation_id=message.conversation_id,
                    role=message.role,
                    content=message.content,
                    created_at=message.created_at,
                )
                for message in messages
            ]
