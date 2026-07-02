"""Document ingestion pipeline: extract, chunk, embed, and store."""

import logging
from pathlib import Path

from app.ingestion.chunker import TextChunker
from app.ingestion.document_loader import DocumentLoader, DocumentLoaderError
from app.memory.chroma import ChromaMemory, ChromaMemoryError
from app.services.embedding_service import EmbeddingService, EmbeddingServiceError

logger = logging.getLogger(__name__)


class IngestionServiceError(Exception):
    """Raised when document ingestion fails."""


class IngestionService:
    """Orchestrates document loading, chunking, embedding, and storage."""

    def __init__(
        self,
        document_loader: DocumentLoader,
        chunker: TextChunker,
        embedding_service: EmbeddingService,
        chroma_memory: ChromaMemory,
    ) -> None:
        self._document_loader = document_loader
        self._chunker = chunker
        self._embedding_service = embedding_service
        self._chroma_memory = chroma_memory

    async def ingest(self, filename: str, content: bytes, source: str | None = None) -> int:
        """Ingest a document and return the number of stored chunks."""
        resolved_source = source or filename
        logger.info("Starting ingestion for %s", filename)

        try:
            text = self._document_loader.extract_text(filename, content)
            chunks = self._chunker.chunk(text)
            if not chunks:
                raise IngestionServiceError("Document produced no chunks")

            embeddings = await self._embedding_service.encode_batch_async(chunks)
            stored = self._chroma_memory.add_chunks(
                chunks=chunks,
                embeddings=embeddings,
                filename=Path(filename).name,
                source=resolved_source,
            )
        except DocumentLoaderError as exc:
            logger.warning("Document loading failed: %s", exc)
            raise IngestionServiceError(str(exc)) from exc
        except EmbeddingServiceError as exc:
            logger.error("Embedding failed during ingestion: %s", exc)
            raise IngestionServiceError("Failed to generate embeddings") from exc
        except ChromaMemoryError as exc:
            logger.error("ChromaDB storage failed: %s", exc)
            raise IngestionServiceError("Failed to store document chunks") from exc

        logger.info("Ingested %s with %d chunks", filename, stored)
        return stored
