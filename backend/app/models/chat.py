"""Pydantic request and response models for the JaneAI API."""

from pydantic import BaseModel, Field


class RootResponse(BaseModel):
    """Response payload for the root endpoint."""

    name: str
    status: str


class HealthResponse(BaseModel):
    """Response payload for the health check endpoint."""

    status: str


class ChatRequest(BaseModel):
    """Incoming chat message from the client."""

    message: str = Field(..., min_length=1, max_length=32_000)


class ChatResponse(BaseModel):
    """Assistant reply returned to the client."""

    response: str
