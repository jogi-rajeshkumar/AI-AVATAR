"""TTS providers: gTTS, pyttsx3, or none (browser fallback)."""
from __future__ import annotations

import io
import os
import logging
import tempfile

logger = logging.getLogger(__name__)


class TTSProvider:
    def synthesize(self, text: str) -> bytes | None:
        """Return audio bytes (MP3/WAV) or None to signal browser fallback."""
        raise NotImplementedError

    @property
    def content_type(self) -> str:
        return "audio/mpeg"


class GTTSProvider(TTSProvider):
    """Google Text-to-Speech – free, no API key, requires internet."""

    def synthesize(self, text: str) -> bytes | None:
        from gtts import gTTS  # type: ignore
        buf = io.BytesIO()
        tts = gTTS(text=text, lang="en")
        tts.write_to_fp(buf)
        buf.seek(0)
        return buf.read()

    @property
    def content_type(self) -> str:
        return "audio/mpeg"


class Pyttsx3Provider(TTSProvider):
    """Offline TTS via pyttsx3 – cross-platform, no internet needed."""

    def synthesize(self, text: str) -> bytes | None:
        import pyttsx3  # type: ignore
        engine = pyttsx3.init()
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp_path = tmp.name
        engine.save_to_file(text, tmp_path)
        engine.runAndWait()
        with open(tmp_path, "rb") as f:
            data = f.read()
        os.unlink(tmp_path)
        return data

    @property
    def content_type(self) -> str:
        return "audio/wav"


class NoopTTSProvider(TTSProvider):
    """Returns None – UI falls back to browser SpeechSynthesis."""

    def synthesize(self, text: str) -> bytes | None:
        return None


def get_tts_provider() -> TTSProvider:
    engine = os.getenv("TTS_ENGINE", "gtts").strip().lower()
    if engine == "gtts":
        try:
            from gtts import gTTS  # noqa: F401
            logger.info("Using gTTS provider")
            return GTTSProvider()
        except ImportError:
            logger.warning("gtts not installed; trying pyttsx3")
    if engine in ("pyttsx3", "gtts"):
        try:
            import pyttsx3  # noqa: F401
            logger.info("Using pyttsx3 provider")
            return Pyttsx3Provider()
        except ImportError:
            logger.warning("pyttsx3 not installed; TTS disabled (browser fallback)")
    logger.info("Using NoopTTS provider (browser SpeechSynthesis will be used)")
    return NoopTTSProvider()
