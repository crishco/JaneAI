"""Intent routing for the JaneAI LangGraph agent."""

from __future__ import annotations

import logging
import re

from app.agents.state import RouteName
from app.services.ollama_service import OllamaService, OllamaServiceError

logger = logging.getLogger(__name__)

TOOL_KEYWORDS = (
    "screen",
    "screenshot",
    "click",
    "mouse",
    "window",
    "desktop",
    "type ",
    "press ",
    "scroll",
    "look at my",
    "open app",
    "move cursor",
)

MEMORY_KEYWORDS = (
    "remember",
    "recall",
    "from my documents",
    "uploaded",
    "in memory",
    "what did i",
    "based on my files",
    "from my notes",
)


class Planner:
    """Chooses whether to chat, retrieve memory, or execute desktop tools."""

    def __init__(self, ollama_service: OllamaService) -> None:
        self._ollama_service = ollama_service

    async def classify(self, message: str) -> RouteName:
        lowered = message.lower()
        if any(keyword in lowered for keyword in TOOL_KEYWORDS):
            logger.info("Planner routed to tools via keyword match")
            return "tools"
        if any(keyword in lowered for keyword in MEMORY_KEYWORDS):
            logger.info("Planner routed to memory via keyword match")
            return "memory"

        prompt = (
            "Classify the user request into exactly one category.\n"
            "Categories:\n"
            "- conversation: general chat, reasoning, coding help\n"
            "- memory: needs retrieved documents or stored knowledge\n"
            "- tools: needs screen inspection or desktop automation\n\n"
            f"User message: {message}\n"
            "Reply with one word only: conversation, memory, or tools."
        )

        try:
            raw = await self._ollama_service.generate_response(prompt)
        except OllamaServiceError as exc:
            logger.warning("Planner LLM fallback to conversation: %s", exc)
            return "conversation"

        normalized = re.sub(r"[^a-z]", "", raw.lower())
        if normalized in {"conversation", "memory", "tools"}:
            logger.info("Planner routed to %s via LLM", normalized)
            return normalized  # type: ignore[return-value]

        logger.info("Planner defaulting to conversation")
        return "conversation"
