"""Chat API routes."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.agents.graph import AgentOrchestrator
from app.core.status import status_manager
from app.models.chat import ChatRequest, ChatResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])


def get_agent(request: Request) -> AgentOrchestrator:
    """Resolve the agent orchestrator from application state."""
    agent = getattr(request.app.state, "agent", None)
    if agent is None:
        logger.error("Agent orchestrator is not available in application state")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Chat service is unavailable",
        )
    return agent


@router.post("", response_model=ChatResponse)
async def chat(
    payload: ChatRequest,
    request: Request,
    agent: AgentOrchestrator = Depends(get_agent),
) -> ChatResponse:
    """Accept a user message and return the assistant response."""
    logger.info("Received chat request (length=%d)", len(payload.message))
    startup_errors = getattr(request.app.state, "startup_errors", [])

    critical_errors = [
        error
        for error in startup_errors
        if "Ollama is unreachable" in error or "Embedding model failed" in error
    ]
    if critical_errors:
        detail = critical_errors[0]
        status_manager.set("Error", detail)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=detail,
        )

    try:
        response, conversation_id = await agent.respond(
            payload.message,
            conversation_id=payload.conversation_id,
        )
    except ValueError as exc:
        logger.warning("Chat request rejected: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except RuntimeError as exc:
        logger.error("Chat request failed: %s", exc)
        status_manager.set("Error", str(exc))
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc

    return ChatResponse(
        response=response,
        conversation_id=conversation_id,
    )
