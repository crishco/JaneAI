"""JaneAI FastAPI application entry point."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI

from app.api.chat import router as chat_router
from app.api.upload import router as upload_router
from app.chat.chatbot import Chatbot
from app.config.settings import Settings, get_settings
from app.database import models as _database_models  # noqa: F401
from app.database.database import close_database, create_tables, init_database
from app.history.history_service import HistoryService
from app.ingestion.chunker import TextChunker
from app.ingestion.document_loader import DocumentLoader
from app.ingestion.ingestion_service import IngestionService
from app.memory.chroma import ChromaMemory
from app.models.chat import HealthResponse, RootResponse
from app.rag.retriever import Retriever
from app.services.embedding_service import EmbeddingService
from app.services.ollama_service import OllamaService

logger = logging.getLogger(__name__)


def configure_logging(settings: Settings) -> None:
    """Configure application-wide logging."""
    logging.basicConfig(
        level=settings.log_level.upper(),
        format=settings.log_format,
    )


def ensure_runtime_directories(settings: Settings) -> None:
    """Create directories required for persistence and uploads."""
    for directory in (
        settings.chroma_persist_directory,
        settings.upload_directory,
        Path(settings.database_url.replace("sqlite:///", "")).parent,
    ):
        Path(directory).mkdir(parents=True, exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Initialize and tear down application resources."""
    settings: Settings = app.state.settings

    logger.info("Starting %s", settings.app_name)
    ensure_runtime_directories(settings)
    init_database(settings)
    create_tables()

    embedding_service = EmbeddingService(settings)
    embedding_service.load()

    chroma_memory = ChromaMemory(settings)
    chroma_memory.initialize()

    retriever = Retriever(chroma_memory, embedding_service, settings)
    history_service = HistoryService()

    document_loader = DocumentLoader(settings)
    chunker = TextChunker(settings)
    ingestion_service = IngestionService(
        document_loader=document_loader,
        chunker=chunker,
        embedding_service=embedding_service,
        chroma_memory=chroma_memory,
    )

    ollama_service = OllamaService(settings)
    app.state.chatbot = Chatbot(
        ollama_service=ollama_service,
        retriever=retriever,
        history_service=history_service,
    )
    app.state.ingestion_service = ingestion_service
    app.state.chroma_memory = chroma_memory
    app.state.embedding_service = embedding_service

    logger.info("%s is ready", settings.app_name)
    yield

    embedding_service.unload()
    chroma_memory.shutdown()
    close_database()
    logger.info("%s shutdown complete", settings.app_name)


def create_app(settings: Settings | None = None) -> FastAPI:
    """Application factory for JaneAI."""
    resolved_settings = settings or get_settings()
    configure_logging(resolved_settings)

    app = FastAPI(
        title=resolved_settings.app_name,
        version=resolved_settings.app_version,
        debug=resolved_settings.debug,
        lifespan=lifespan,
    )
    app.state.settings = resolved_settings

    app.include_router(chat_router)
    app.include_router(upload_router)

    @app.get("/", response_model=RootResponse)
    async def root() -> RootResponse:
        return RootResponse(name=resolved_settings.app_name, status="running")

    @app.get("/health", response_model=HealthResponse)
    async def health() -> HealthResponse:
        return HealthResponse(status="healthy")

    return app


app = create_app()
