"""Sentence-transformer embedding service."""

import asyncio
import logging
from functools import partial

from sentence_transformers import SentenceTransformer

from app.config.settings import Settings

logger = logging.getLogger(__name__)


class EmbeddingServiceError(Exception):
    """Raised when embedding generation fails."""


class EmbeddingService:
    """Generates text embeddings using sentence-transformers."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._model_name = settings.embedding_model
        self._model: SentenceTransformer | None = None

    def load(self) -> None:
        """Load the embedding model into memory."""
        if self._model is not None:
            logger.debug("Embedding model already loaded")
            return

        logger.info("Loading embedding model: %s", self._model_name)
        try:
            self._model = SentenceTransformer(self._model_name)
        except Exception as exc:
            logger.error("Failed to load embedding model %s", self._model_name)
            raise EmbeddingServiceError("Failed to load embedding model") from exc

        logger.info("Embedding model ready")

    def unload(self) -> None:
        """Release the embedding model."""
        self._model = None
        logger.info("Embedding model unloaded")

    def _ensure_loaded(self) -> SentenceTransformer:
        if self._model is None:
            raise EmbeddingServiceError("Embedding model has not been loaded")
        return self._model

    def encode(self, text: str) -> list[float]:
        """Encode a single text into an embedding vector."""
        normalized = text.strip()
        if not normalized:
            raise EmbeddingServiceError("Cannot embed empty text")

        model = self._ensure_loaded()
        try:
            vector = model.encode(normalized, convert_to_numpy=True)
        except Exception as exc:
            logger.error("Failed to encode text")
            raise EmbeddingServiceError("Failed to generate embedding") from exc

        return vector.tolist()

    def encode_batch(self, texts: list[str]) -> list[list[float]]:
        """Encode multiple texts into embedding vectors."""
        if not texts:
            return []

        model = self._ensure_loaded()
        try:
            vectors = model.encode(texts, convert_to_numpy=True, show_progress_bar=False)
        except Exception as exc:
            logger.error("Failed to encode batch of %d texts", len(texts))
            raise EmbeddingServiceError("Failed to generate embeddings") from exc

        return [vector.tolist() for vector in vectors]

    async def encode_async(self, text: str) -> list[float]:
        """Run single-text encoding without blocking the event loop."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, partial(self.encode, text))

    async def encode_batch_async(self, texts: list[str]) -> list[list[float]]:
        """Run batch encoding without blocking the event loop."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, partial(self.encode_batch, texts))
