"""AI Avatar – combined backend (FastAPI).

Endpoints
---------
POST /api/stt   – audio → transcript
POST /api/chat  – transcript → response + emotion + sources
POST /api/tts   – text → audio bytes
GET  /api/health
"""
from __future__ import annotations

import logging
import os
import uuid
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel

from providers.emotion import get_emotion_provider
from providers.llm import get_llm_provider
from providers.search import SearchResult, get_search_provider
from providers.stt import get_stt_provider
from providers.tts import get_tts_provider

logging.basicConfig(level=logging.INFO, format="%(levelname)s │ %(name)s │ %(message)s")
logger = logging.getLogger(__name__)

# ── Initialise providers (lazy singletons) ──────────────────────────────────
_stt = get_stt_provider()
_llm = get_llm_provider()
_search = get_search_provider()
_emotion = get_emotion_provider()
_tts = get_tts_provider()

# ── Conversation history store (in-memory, keyed by conversation_id) ────────
_histories: Dict[str, List[Dict[str, str]]] = {}

# ── FastAPI app ──────────────────────────────────────────────────────────────
app = FastAPI(title="AI Avatar API", version="0.1.0")

_origin = os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[_origin, "http://localhost:3000", "http://localhost:4173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Models ───────────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    transcript: str
    conversation_id: Optional[str] = None


class SourceModel(BaseModel):
    title: str
    url: str
    snippet: str


class ChatResponse(BaseModel):
    conversation_id: str
    response: str
    emotion: str
    emotion_confidence: float
    sources: List[SourceModel]
    tts_available: bool


class TTSRequest(BaseModel):
    text: str


class STTResponse(BaseModel):
    transcript: str
    stt_available: bool


# ── Health ───────────────────────────────────────────────────────────────────

@app.get("/api/health")
def health() -> Dict[str, Any]:
    return {
        "status": "ok",
        "stt": type(_stt).__name__,
        "llm": type(_llm).__name__,
        "search": type(_search).__name__,
        "emotion": type(_emotion).__name__,
        "tts": type(_tts).__name__,
    }


# ── STT ──────────────────────────────────────────────────────────────────────

@app.post("/api/stt", response_model=STTResponse)
async def stt(audio: UploadFile = File(...)) -> STTResponse:
    from providers.stt import NoopSTTProvider

    audio_bytes = await audio.read()
    mime = audio.content_type or "audio/webm"
    try:
        transcript = _stt.transcribe(audio_bytes, mime)
    except Exception as exc:
        logger.error("STT error: %s", exc)
        raise HTTPException(status_code=500, detail=f"STT failed: {exc}") from exc

    return STTResponse(
        transcript=transcript,
        stt_available=not isinstance(_stt, NoopSTTProvider),
    )


# ── Chat ─────────────────────────────────────────────────────────────────────

@app.post("/api/chat", response_model=ChatResponse)
def chat(req: ChatRequest) -> ChatResponse:
    from providers.tts import NoopTTSProvider

    if not req.transcript.strip():
        raise HTTPException(status_code=422, detail="transcript must not be empty")

    conv_id = req.conversation_id or str(uuid.uuid4())

    # 1. Web search for context
    search_results: List[SearchResult] = []
    try:
        search_results = _search.search(req.transcript, max_results=4)
    except Exception as exc:
        logger.warning("Search failed: %s", exc)

    context_snippets = [
        f"{r.title}: {r.snippet}" for r in search_results if r.snippet
    ]

    # 2. LLM response
    try:
        response_text = _llm.generate(req.transcript, context_snippets)
    except Exception as exc:
        logger.error("LLM error: %s", exc)
        response_text = f"Sorry, I encountered an error: {exc}"

    # 3. Emotion detection on the LLM response
    try:
        emotion_label, confidence = _emotion.detect(response_text)
    except Exception as exc:
        logger.warning("Emotion detection failed: %s", exc)
        emotion_label, confidence = "neutral", 0.5

    # 4. Store conversation
    history = _histories.setdefault(conv_id, [])
    history.append({"role": "user", "content": req.transcript})
    history.append({"role": "assistant", "content": response_text})
    if len(history) > 40:
        _histories[conv_id] = history[-40:]

    return ChatResponse(
        conversation_id=conv_id,
        response=response_text,
        emotion=emotion_label,
        emotion_confidence=confidence,
        sources=[
            SourceModel(title=r.title, url=r.url, snippet=r.snippet)
            for r in search_results
        ],
        tts_available=not isinstance(_tts, NoopTTSProvider),
    )


# ── TTS ──────────────────────────────────────────────────────────────────────

@app.post("/api/tts")
def tts(req: TTSRequest) -> Response:
    if not req.text.strip():
        raise HTTPException(status_code=422, detail="text must not be empty")
    try:
        audio_bytes = _tts.synthesize(req.text)
    except Exception as exc:
        logger.error("TTS error: %s", exc)
        raise HTTPException(status_code=500, detail=f"TTS failed: {exc}") from exc

    if audio_bytes is None:
        raise HTTPException(status_code=204, detail="TTS not available; use browser fallback")

    return Response(content=audio_bytes, media_type=_tts.content_type)


# ── Entry-point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn

    host = os.getenv("BACKEND_HOST", "0.0.0.0")
    port = int(os.getenv("BACKEND_PORT", "8000"))
    uvicorn.run("main:app", host=host, port=port, reload=True)
