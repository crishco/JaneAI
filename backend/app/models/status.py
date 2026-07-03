"""Pydantic models for runtime status endpoints."""

from pydantic import BaseModel, Field


class StatusResponse(BaseModel):
    """Current JaneAI activity and accumulated errors."""

    status: str
    detail: str = ""
    errors: list[str] = Field(default_factory=list)
    updated_at: str
    backend_healthy: bool = True


class VoiceTranscriptionResponse(BaseModel):
    """Speech-to-text result."""

    text: str


class VoiceSpeakRequest(BaseModel):
    """Text payload for speech synthesis."""

    text: str = Field(..., min_length=1, max_length=8_000)
