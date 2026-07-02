"""Text chunking utilities for document ingestion."""

import logging

from app.config.settings import Settings

logger = logging.getLogger(__name__)


class TextChunker:
    """Splits long text into overlapping word-based chunks."""

    def __init__(self, settings: Settings) -> None:
        self._chunk_size = settings.chunk_size_words
        self._overlap = settings.chunk_overlap_words

    def chunk(self, text: str) -> list[str]:
        """Split text into chunks of approximately chunk_size words."""
        normalized = " ".join(text.split())
        if not normalized:
            return []

        words = normalized.split()
        if len(words) <= self._chunk_size:
            return [normalized]

        chunks: list[str] = []
        start = 0
        step = max(self._chunk_size - self._overlap, 1)

        while start < len(words):
            end = start + self._chunk_size
            chunk = " ".join(words[start:end]).strip()
            if chunk:
                chunks.append(chunk)
            if end >= len(words):
                break
            start += step

        logger.debug(
            "Split text into %d chunks (size=%d, overlap=%d)",
            len(chunks),
            self._chunk_size,
            self._overlap,
        )
        return chunks
