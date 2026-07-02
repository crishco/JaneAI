"""Chat business logic layer."""

import logging
from dataclasses import dataclass

from app.history.history_service import HistoryService, HistoryServiceError
from app.rag.retriever import Retriever, RetrieverError
from app.services.ollama_service import OllamaService, OllamaServiceError

logger = logging.getLogger(__name__)


class ChatbotError(Exception):
    """Raised when the chatbot cannot produce a response."""


@dataclass(frozen=True)
class ChatResult:
    """Result of a completed chat turn."""

    response: str
    conversation_id: str


class Chatbot:
    """Orchestrates RAG retrieval, history persistence, and LLM generation."""

    def __init__(
        self,
        ollama_service: OllamaService,
        retriever: Retriever,
        history_service: HistoryService,
    ) -> None:
        self._ollama_service = ollama_service
        self._retriever = retriever
        self._history_service = history_service

    async def respond(
        self,
        message: str,
        conversation_id: str | None = None,
    ) -> ChatResult:
        """Process a user message and return the assistant reply."""
        normalized_message = message.strip()
        if not normalized_message:
            raise ChatbotError("Message cannot be empty")

        conversation_id = self._resolve_conversation_id(conversation_id)

        logger.info(
            "Processing chat message (conversation=%s, length=%d, model=%s)",
            conversation_id,
            len(normalized_message),
            self._ollama_service.model,
        )

        try:
            self._history_service.add_message(conversation_id, "user", normalized_message)

            chunks = await self._retriever.retrieve(normalized_message)
            augmented_prompt = self._retriever.build_prompt(normalized_message, chunks)

            response = await self._ollama_service.generate_response(augmented_prompt)
            self._history_service.add_message(conversation_id, "assistant", response)
        except HistoryServiceError as exc:
            logger.error("History service failure: %s", exc)
            raise ChatbotError("Failed to persist conversation history") from exc
        except RetrieverError as exc:
            logger.warning("Retrieval failed, continuing without context: %s", exc)
            try:
                response = await self._ollama_service.generate_response(normalized_message)
                self._history_service.add_message(conversation_id, "assistant", response)
            except OllamaServiceError as llm_exc:
                logger.error("LLM service failure: %s", llm_exc)
                raise ChatbotError("Failed to generate a response") from llm_exc
        except OllamaServiceError as exc:
            logger.error("LLM service failure: %s", exc)
            raise ChatbotError("Failed to generate a response") from exc

        return ChatResult(response=response, conversation_id=conversation_id)

    def _resolve_conversation_id(self, conversation_id: str | None) -> str:
        if conversation_id is None:
            return self._history_service.create_conversation()

        if not self._history_service.conversation_exists(conversation_id):
            raise ChatbotError(f"Conversation not found: {conversation_id}")

        return conversation_id
