"""JaneAI FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI

from app.api.chat import router as chat_router
from app.chat.chatbot import Chatbot
from app.config.settings import Settings, get_settings
from app.database.database import close_database, init_database
from app.memory.chroma import ChromaMemory
from app.models.chat import HealthResponse, RootResponse
from app.services.ollama_service import OllamaService

logger = logging.getLogger(__name__)


def configure_logging(settings: Settings) -> None:
    """Configure application-wide logging."""
    logging.basicConfig(
        level=settings.log_level.upper(),
        format=settings.log_format,
    )


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Initialize and tear down application resources."""
    settings: Settings = app.state.settings

    logger.info("Starting %s", settings.app_name)
    init_database(settings)

    chroma_memory = ChromaMemory(settings)
    chroma_memory.initialize()

    ollama_service = OllamaService(settings)
    app.state.chatbot = Chatbot(ollama_service)
    app.state.chroma_memory = chroma_memory

    logger.info("%s is ready", settings.app_name)
    yield

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

    @app.get("/", response_model=RootResponse)
    async def root() -> RootResponse:
        return RootResponse(name=resolved_settings.app_name, status="running")

    @app.get("/health", response_model=HealthResponse)
    async def health() -> HealthResponse:
        return HealthResponse(status="healthy")

    return app


app = create_app()
