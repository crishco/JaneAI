"""Whisper-based speech-to-text service."""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path

import whisper

from app.config.settings import Settings

logger = logging.getLogger(__name__)


class SpeechToTextError(Exception):
    """Raised when transcription fails."""


class SpeechToTextService:
    """Transcribes user audio using a local Whisper model."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._model_name = settings.whisper_model
        self._model: whisper.Whisper | None = None

    @property
    def is_loaded(self) -> bool:
        return self._model is not None

    def load(self) -> None:
        if self._model is not None:
            return

        logger.info("Loading Whisper model: %s", self._model_name)
        try:
            self._model = whisper.load_model(self._model_name)
        except Exception as exc:
            logger.exception("Failed to load Whisper model %s", self._model_name)
            raise SpeechToTextError(
                f"Failed to load Whisper model '{self._model_name}': {exc}"
            ) from exc

        logger.info("Whisper model ready")

    def unload(self) -> None:
        self._model = None
        logger.info("Whisper model unloaded")

    def transcribe(self, audio_bytes: bytes, filename: str = "audio.webm") -> str:
        if not audio_bytes:
            raise SpeechToTextError("Audio payload is empty")
        if self._model is None:
            raise SpeechToTextError("Whisper model has not been loaded")

        suffix = Path(filename).suffix or ".webm"
        temp_path: str | None = None
        try:
            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as handle:
                handle.write(audio_bytes)
                temp_path = handle.name

            result = self._model.transcribe(temp_path, fp16=False)
            text = str(result.get("text", "")).strip()
            if not text:
                raise SpeechToTextError("Whisper returned empty transcription")
            logger.info("Transcribed %d characters from audio", len(text))
            return text
        except SpeechToTextError:
            raise
        except Exception as exc:
            logger.exception("Whisper transcription failed")
            raise SpeechToTextError(f"Transcription failed: {exc}") from exc
        finally:
            if temp_path:
                Path(temp_path).unlink(missing_ok=True)
