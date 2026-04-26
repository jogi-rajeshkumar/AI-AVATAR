"""STT providers: Whisper (local) or none (text fallback in UI)."""
from __future__ import annotations

import io
import os
import logging
import tempfile

logger = logging.getLogger(__name__)


class STTProvider:
    def transcribe(self, audio_bytes: bytes, mime_type: str = "audio/webm") -> str:
        raise NotImplementedError


class WhisperProvider(STTProvider):
    """OpenAI Whisper (local) via the `openai-whisper` package."""

    def __init__(self, model_name: str = "base") -> None:
        import whisper  # type: ignore
        logger.info("Loading Whisper model '%s' …", model_name)
        self._model = whisper.load_model(model_name)

    def transcribe(self, audio_bytes: bytes, mime_type: str = "audio/webm") -> str:
        suffix = _ext_from_mime(mime_type)
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name
        try:
            result = self._model.transcribe(tmp_path)
            return result["text"].strip()
        finally:
            os.unlink(tmp_path)


class FasterWhisperProvider(STTProvider):
    """Faster-Whisper (CTranslate2) – faster and lower memory than openai-whisper."""

    def __init__(self, model_name: str = "base") -> None:
        from faster_whisper import WhisperModel  # type: ignore
        logger.info("Loading faster-whisper model '%s' …", model_name)
        self._model = WhisperModel(model_name, device="cpu", compute_type="int8")

    def transcribe(self, audio_bytes: bytes, mime_type: str = "audio/webm") -> str:
        suffix = _ext_from_mime(mime_type)
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name
        try:
            segments, _ = self._model.transcribe(tmp_path)
            return " ".join(s.text for s in segments).strip()
        finally:
            os.unlink(tmp_path)


class NoopSTTProvider(STTProvider):
    """Returns empty string – UI will show a text input field instead."""

    def transcribe(self, audio_bytes: bytes, mime_type: str = "audio/webm") -> str:
        return ""


def _ext_from_mime(mime: str) -> str:
    mapping = {
        "audio/webm": ".webm",
        "audio/ogg": ".ogg",
        "audio/mp4": ".mp4",
        "audio/wav": ".wav",
        "audio/mpeg": ".mp3",
    }
    return mapping.get(mime.split(";")[0].strip(), ".webm")


def get_stt_provider() -> STTProvider:
    engine = os.getenv("STT_ENGINE", "none").strip().lower()
    model_name = os.getenv("WHISPER_MODEL", "base").strip()
    if engine == "faster-whisper":
        try:
            provider = FasterWhisperProvider(model_name)
            logger.info("Using faster-whisper STT provider")
            return provider
        except ImportError:
            logger.warning("faster-whisper not installed; trying openai-whisper")
    if engine in ("whisper", "faster-whisper"):
        try:
            provider = WhisperProvider(model_name)
            logger.info("Using openai-whisper STT provider")
            return provider
        except ImportError:
            logger.warning("openai-whisper not installed; STT disabled (text input fallback)")
    logger.info("Using NoopSTT provider (text input fallback in UI)")
    return NoopSTTProvider()
