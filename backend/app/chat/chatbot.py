"""Chat business logic layer."""

import logging

from app.services.ollama_service import OllamaService, OllamaServiceError

logger = logging.getLogger(__name__)


class ChatbotError(Exception):
    """Raised when the chatbot cannot produce a response."""


class Chatbot:
    """Orchestrates conversation flow and delegates LLM calls to OllamaService."""

    def __init__(self, ollama_service: OllamaService) -> None:
        self._ollama_service = ollama_service

    async def respond(self, message: str) -> str:
        """Process a user message and return the assistant reply."""
        normalized_message = message.strip()
        if not normalized_message:
            raise ChatbotError("Message cannot be empty")

        logger.info(
            "Processing chat message (length=%d, model=%s)",
            len(normalized_message),
            self._ollama_service.model,
        )

        try:
            response = await self._ollama_service.generate_response(normalized_message)
        except OllamaServiceError as exc:
            logger.error("LLM service failure: %s", exc)
            raise ChatbotError("Failed to generate a response") from exc

        return response
