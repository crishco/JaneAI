"""Document upload API routes."""

import logging
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status

from app.ingestion.ingestion_service import IngestionService, IngestionServiceError
from app.models.upload import UploadResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/upload", tags=["upload"])


def get_ingestion_service(request: Request) -> IngestionService:
    """Resolve the ingestion service from application state."""
    service = getattr(request.app.state, "ingestion_service", None)
    if service is None:
        logger.error("Ingestion service is not available in application state")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Upload service is unavailable",
        )
    return service


def get_upload_limits(request: Request) -> tuple[int, set[str]]:
    """Return max upload size in bytes and allowed extensions."""
    settings = request.app.state.settings
    max_bytes = settings.upload_max_file_size_mb * 1024 * 1024
    allowed = {ext.lower() for ext in settings.allowed_upload_extensions}
    return max_bytes, allowed


@router.post("", response_model=UploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    ingestion_service: IngestionService = Depends(get_ingestion_service),
    limits: tuple[int, set[str]] = Depends(get_upload_limits),
) -> UploadResponse:
    """Accept a document, extract text, embed chunks, and store them in ChromaDB."""
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename is required",
        )

    max_bytes, allowed_extensions = limits
    extension = Path(file.filename).suffix.lower()
    if extension not in allowed_extensions:
        supported = ", ".join(sorted(allowed_extensions))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type '{extension}'. Supported: {supported}",
        )

    content = await file.read()
    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty",
        )
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds maximum size of {max_bytes // (1024 * 1024)} MB",
        )

    logger.info("Received upload: %s (%d bytes)", file.filename, len(content))

    try:
        chunk_count = await ingestion_service.ingest(
            filename=file.filename,
            content=content,
            source=file.filename,
        )
    except IngestionServiceError as exc:
        logger.warning("Upload ingestion failed for %s: %s", file.filename, exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    return UploadResponse(status="success", chunks=chunk_count)
