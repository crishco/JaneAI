"""Voice transcription and synthesis API routes."""

import logging

from fastapi import APIRouter, File, HTTPException, Request, UploadFile, status
from fastapi.responses import Response

from app.models.status import VoiceSpeakRequest, VoiceTranscriptionResponse
from app.voice.speech_to_text import SpeechToTextError, SpeechToTextService
from app.voice.text_to_speech import TextToSpeechError, TextToSpeechService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/voice", tags=["voice"])


def get_stt_service(request: Request) -> SpeechToTextService | None:
    return getattr(request.app.state, "speech_to_text", None)


def get_tts_service(request: Request) -> TextToSpeechService | None:
    return getattr(request.app.state, "text_to_speech", None)


@router.post("/transcribe", response_model=VoiceTranscriptionResponse)
async def transcribe_audio(
    request: Request,
    audio: UploadFile = File(...),
) -> VoiceTranscriptionResponse:
    """Transcribe uploaded audio using Whisper."""
    service = get_stt_service(request)
    startup_errors = getattr(request.app.state, "startup_errors", [])
    if service is None or not service.is_loaded:
        detail = "Speech-to-text is unavailable."
        if startup_errors:
            detail = f"{detail} {'; '.join(startup_errors)}"
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=detail)

    payload = await audio.read()
    filename = audio.filename or "audio.webm"
    logger.info("Received audio for transcription (%d bytes)", len(payload))

    try:
        text = service.transcribe(payload, filename=filename)
    except SpeechToTextError as exc:
        logger.warning("Transcription failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    return VoiceTranscriptionResponse(text=text)


@router.post("/speak")
async def speak_text(
    payload: VoiceSpeakRequest,
    request: Request,
) -> Response:
    """Synthesize speech audio from text using Piper."""
    service = get_tts_service(request)
    if service is None or not service.is_loaded:
        detail = "Text-to-speech is unavailable. Configure JANE_PIPER_MODEL_PATH."
        startup_errors = getattr(request.app.state, "startup_errors", [])
        if startup_errors:
            detail = f"{detail} {'; '.join(startup_errors)}"
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=detail)

    try:
        audio_bytes = service.synthesize_wav(payload.text)
    except TextToSpeechError as exc:
        logger.warning("Speech synthesis failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    return Response(content=audio_bytes, media_type="audio/wav")
