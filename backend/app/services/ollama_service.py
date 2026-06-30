"""Ollama LLM integration service."""

import logging
from typing import Any

import httpx

from app.config.settings import Settings

logger = logging.getLogger(__name__)


class OllamaServiceError(Exception):
    """Raised when Ollama returns an error or is unreachable."""


class OllamaService:
    """Handles communication with a local Ollama instance."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._base_url = settings.ollama_base_url.rstrip("/")
        self._model = settings.ollama_model
        self._timeout = settings.ollama_timeout_seconds

    @property
    def model(self) -> str:
        return self._model

    async def generate_response(self, message: str) -> str:
        """Send a user message to Ollama and return the assistant reply."""
        payload: dict[str, Any] = {
            "model": self._model,
            "messages": [{"role": "user", "content": message}],
            "stream": False,
        }

        url = f"{self._base_url}/api/chat"
        logger.debug("Sending chat request to Ollama model=%s", self._model)

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
        except httpx.TimeoutException as exc:
            logger.error("Ollama request timed out after %ss", self._timeout)
            raise OllamaServiceError("Ollama request timed out") from exc
        except httpx.HTTPStatusError as exc:
            logger.error(
                "Ollama returned HTTP %s: %s",
                exc.response.status_code,
                exc.response.text,
            )
            raise OllamaServiceError(
                f"Ollama request failed with status {exc.response.status_code}"
            ) from exc
        except httpx.RequestError as exc:
            logger.error("Failed to connect to Ollama at %s", self._base_url)
            raise OllamaServiceError("Unable to connect to Ollama") from exc

        data = response.json()
        content = self._extract_content(data)
        logger.debug("Received response from Ollama (%d chars)", len(content))
        return content

    @staticmethod
    def _extract_content(data: dict[str, Any]) -> str:
        message = data.get("message")
        if not isinstance(message, dict):
            raise OllamaServiceError("Ollama response missing message payload")

        content = message.get("content")
        if not isinstance(content, str) or not content.strip():
            raise OllamaServiceError("Ollama returned an empty response")

        return content.strip()
