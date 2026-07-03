"""JaneAI FastAPI application entry point."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.agents.executor import ToolExecutor
from app.agents.graph import AgentGraph, AgentOrchestrator
from app.agents.planner import Planner
from app.api.chat import router as chat_router
from app.api.status import router as status_router
from app.api.upload import router as upload_router
from app.api.voice import router as voice_router
from app.config.settings import Settings, get_settings
from app.core.status import status_manager
from app.database import models as _database_models  # noqa: F401
from app.database.database import close_database, create_tables, init_database
from app.desktop.screen_control import ScreenControlService
from app.desktop.screenshot import ScreenCaptureService
from app.history.history_service import HistoryService
from app.ingestion.chunker import TextChunker
from app.ingestion.document_loader import DocumentLoader
from app.ingestion.ingestion_service import IngestionService
from app.memory.chroma import ChromaMemory
from app.models.chat import HealthResponse, RootResponse
from app.rag.retriever import Retriever
from app.services.embedding_service import EmbeddingService, EmbeddingServiceError
from app.services.ollama_service import OllamaService
from app.tools.tool_registry import ToolRegistry
from app.voice.speech_to_text import SpeechToTextError, SpeechToTextService
from app.voice.text_to_speech import TextToSpeechError, TextToSpeechService

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


async def verify_ollama(settings: Settings) -> None:
    """Ensure Ollama is reachable before accepting traffic."""
    url = f"{settings.ollama_base_url.rstrip('/')}/api/tags"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url)
            response.raise_for_status()
    except Exception as exc:
        message = (
            f"Ollama is unreachable at {settings.ollama_base_url}. "
            f"Start Ollama and pull model '{settings.ollama_model}'. Details: {exc}"
        )
        status_manager.add_startup_error(message)
        logger.error(message)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Initialize and tear down application resources."""
    settings: Settings = app.state.settings
    startup_errors: list[str] = []
    app.state.startup_errors = startup_errors

    logger.info("Starting %s", settings.app_name)
    status_manager.set("Starting", "Initializing services")
    ensure_runtime_directories(settings)

    init_database(settings)
    create_tables()

    embedding_service = EmbeddingService(settings)
    try:
        embedding_service.load()
    except EmbeddingServiceError as exc:
        message = f"Embedding model failed to load: {exc}"
        startup_errors.append(message)
        status_manager.add_startup_error(message)
        logger.error(message)

    chroma_memory = ChromaMemory(settings)
    try:
        chroma_memory.initialize()
    except Exception as exc:
        message = f"ChromaDB failed to initialize: {exc}"
        startup_errors.append(message)
        status_manager.add_startup_error(message)
        logger.error(message)

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
    await verify_ollama(settings)

    screen_capture = ScreenCaptureService()
    screen_control = ScreenControlService()
    tool_registry = ToolRegistry(screen_capture, screen_control)
    planner = Planner(ollama_service)
    tool_executor = ToolExecutor(ollama_service, tool_registry)
    agent_graph = AgentGraph(
        ollama_service=ollama_service,
        retriever=retriever,
        history_service=history_service,
        planner=planner,
        tool_executor=tool_executor,
    )
    app.state.agent = AgentOrchestrator(agent_graph, history_service)

    speech_to_text = SpeechToTextService(settings)
    try:
        speech_to_text.load()
        app.state.speech_to_text = speech_to_text
    except SpeechToTextError as exc:
        message = f"Whisper failed to load: {exc}"
        startup_errors.append(message)
        status_manager.add_startup_error(message)
        app.state.speech_to_text = None
        logger.error(message)

    text_to_speech = TextToSpeechService(settings)
    if text_to_speech.is_configured:
        try:
            text_to_speech.load()
            app.state.text_to_speech = text_to_speech
        except TextToSpeechError as exc:
            message = f"Piper failed to load: {exc}"
            startup_errors.append(message)
            status_manager.add_startup_error(message)
            app.state.text_to_speech = None
            logger.error(message)
    else:
        app.state.text_to_speech = None
        logger.info("Piper TTS skipped (JANE_PIPER_MODEL_PATH not configured)")

    app.state.ingestion_service = ingestion_service
    app.state.chroma_memory = chroma_memory
    app.state.embedding_service = embedding_service
    app.state.ollama_service = ollama_service

    if startup_errors:
        status_manager.set("Degraded", "Some services failed to start")
        logger.warning("JaneAI started in degraded mode with %d startup error(s)", len(startup_errors))
    else:
        status_manager.set("Idle", "Ready")
        logger.info("%s is ready", settings.app_name)

    yield

    if getattr(app.state, "speech_to_text", None) is not None:
        app.state.speech_to_text.unload()
    if getattr(app.state, "text_to_speech", None) is not None:
        app.state.text_to_speech.unload()

    embedding_service.unload()
    chroma_memory.shutdown()
    close_database()
    status_manager.set("Stopped", "Shutdown complete")
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

    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(resolved_settings.cors_origins),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(chat_router)
    app.include_router(upload_router)
    app.include_router(voice_router)
    app.include_router(status_router)

    @app.get("/", response_model=RootResponse)
    async def root() -> RootResponse:
        return RootResponse(name=resolved_settings.app_name, status="running")

    @app.get("/health", response_model=HealthResponse)
    async def health() -> HealthResponse:
        startup_errors = getattr(app.state, "startup_errors", [])
        if startup_errors:
            return HealthResponse(status="degraded")
        return HealthResponse(status="healthy")

    return app


app = create_app()
