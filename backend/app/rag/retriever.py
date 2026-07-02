"""Retrieval-augmented generation utilities."""

import logging

from app.config.settings import Settings
from app.memory.chroma import ChromaMemory, ChromaMemoryError, RetrievedChunk
from app.services.embedding_service import EmbeddingService, EmbeddingServiceError

logger = logging.getLogger(__name__)


class RetrieverError(Exception):
    """Raised when retrieval fails."""


class Retriever:
    """Searches ChromaDB for relevant context and builds augmented prompts."""

    def __init__(
        self,
        chroma_memory: ChromaMemory,
        embedding_service: EmbeddingService,
        settings: Settings,
    ) -> None:
        self._chroma_memory = chroma_memory
        self._embedding_service = embedding_service
        self._top_k = settings.retrieval_top_k

    async def retrieve(self, query: str) -> list[RetrievedChunk]:
        """Return the most relevant document chunks for a query."""
        normalized_query = query.strip()
        if not normalized_query:
            return []

        try:
            query_embedding = await self._embedding_service.encode_async(normalized_query)
            chunks = self._chroma_memory.search(query_embedding, self._top_k)
        except EmbeddingServiceError as exc:
            logger.error("Failed to embed query for retrieval: %s", exc)
            raise RetrieverError("Failed to embed query") from exc
        except ChromaMemoryError as exc:
            logger.error("Vector search failed: %s", exc)
            raise RetrieverError("Failed to retrieve context") from exc

        logger.info("Retrieved %d context chunks for query", len(chunks))
        return chunks

    @staticmethod
    def build_prompt(user_message: str, chunks: list[RetrievedChunk]) -> str:
        """Inject retrieved context into the user prompt."""
        if not chunks:
            return user_message

        context_blocks = []
        for index, chunk in enumerate(chunks, start=1):
            context_blocks.append(
                "\n".join(
                    [
                        f"[Source {index}]",
                        f"Filename: {chunk.filename}",
                        f"Source: {chunk.source}",
                        f"Content: {chunk.chunk}",
                    ]
                )
            )

        context = "\n\n".join(context_blocks)
        return (
            "Use the following retrieved context to answer the user's question. "
            "If the context does not contain enough information, say so clearly.\n\n"
            f"Context:\n{context}\n\n"
            f"Question: {user_message}"
        )
