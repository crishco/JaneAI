"""Pydantic models for document upload."""

from pydantic import BaseModel


class UploadResponse(BaseModel):
    """Response payload after ingesting a document."""

    status: str
    chunks: int
