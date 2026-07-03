"""Piper text-to-speech service."""

from __future__ import annotations

import io
import logging
import wave
from pathlib import Path

from app.config.settings import Settings

logger = logging.getLogger(__name__)


class TextToSpeechError(Exception):
    """Raised when speech synthesis fails."""


class TextToSpeechService:
    """Generates spoken audio using a local Piper voice model."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._voice = None
        self._model_path = settings.piper_model_path.strip()
        self._config_path = settings.piper_config_path.strip()

    @property
    def is_loaded(self) -> bool:
        return self._voice is not None

    @property
    def is_configured(self) -> bool:
        return bool(self._model_path)

    def load(self) -> None:
        if self._voice is not None:
            return
        if not self._model_path:
            raise TextToSpeechError(
                "Piper model path is not configured. Set JANE_PIPER_MODEL_PATH."
            )

        model_path = Path(self._model_path)
        if not model_path.exists():
            raise TextToSpeechError(f"Piper model not found at {model_path}")

        config_path = self._config_path or str(model_path.with_suffix(".onnx.json"))
        if not Path(config_path).exists():
            raise TextToSpeechError(f"Piper config not found at {config_path}")

        logger.info("Loading Piper voice from %s", model_path)
        try:
            from piper.voice import PiperVoice

            self._voice = PiperVoice.load(str(model_path), config_path=str(config_path))
        except Exception as exc:
            logger.exception("Failed to load Piper voice")
            raise TextToSpeechError(f"Failed to load Piper voice: {exc}") from exc

        logger.info("Piper voice ready")

    def unload(self) -> None:
        self._voice = None
        logger.info("Piper voice unloaded")

    def synthesize_wav(self, text: str) -> bytes:
        normalized = text.strip()
        if not normalized:
            raise TextToSpeechError("Cannot synthesize empty text")
        if self._voice is None:
            raise TextToSpeechError("Piper voice has not been loaded")

        try:
            buffer = io.BytesIO()
            with wave.open(buffer, "wb") as wav_file:
                self._voice.synthesize_wav(normalized, wav_file)

            audio_bytes = buffer.getvalue()
            if not audio_bytes:
                raise TextToSpeechError("Piper returned empty audio")
            logger.info("Synthesized %d bytes of audio", len(audio_bytes))
            return audio_bytes
        except TextToSpeechError:
            raise
        except Exception as exc:
            logger.exception("Piper synthesis failed")
            raise TextToSpeechError(f"Speech synthesis failed: {exc}") from exc
