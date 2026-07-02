"""Chat API routes."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.chat.chatbot import Chatbot, ChatbotError
from app.models.chat import ChatRequest, ChatResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])


def get_chatbot(request: Request) -> Chatbot:
    """Resolve the chatbot instance from application state."""
    chatbot = getattr(request.app.state, "chatbot", None)
    if chatbot is None:
        logger.error("Chatbot is not available in application state")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Chat service is unavailable",
        )
    return chatbot


@router.post("", response_model=ChatResponse)
async def chat(
    payload: ChatRequest,
    chatbot: Chatbot = Depends(get_chatbot),
) -> ChatResponse:
    """Accept a user message and return the assistant response."""
    logger.info("Received chat request (length=%d)", len(payload.message))

    try:
        result = await chatbot.respond(
            payload.message,
            conversation_id=payload.conversation_id,
        )
    except ChatbotError as exc:
        logger.warning("Chat request failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc

    return ChatResponse(
        response=result.response,
        conversation_id=result.conversation_id,
    )
