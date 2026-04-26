"""Emotion providers: transformers pipeline, VADER, or heuristic fallback."""
from __future__ import annotations

import os
import logging
import re
from typing import Tuple

logger = logging.getLogger(__name__)

EMOTION_LABELS = ("happy", "sad", "angry", "fearful", "surprised", "neutral")

# Simple keyword heuristic used as last-resort fallback
_KEYWORD_MAP = {
    "happy": r"\b(happy|joy|great|wonderful|amazing|love|excited|fantastic|awesome|glad)\b",
    "sad": r"\b(sad|depressed|unhappy|cry|grief|sorrow|miss|lost|hurt|unfortunate)\b",
    "angry": r"\b(angry|mad|furious|hate|rage|annoyed|frustrated|disgusting|terrible)\b",
    "fearful": r"\b(fear|scared|afraid|worried|anxious|nervous|terrified|dread)\b",
    "surprised": r"\b(surprised|wow|shocked|unexpected|amazing|unbelievable|incredible)\b",
}


class EmotionProvider:
    def detect(self, text: str) -> Tuple[str, float]:
        """Return (emotion_label, confidence 0-1)."""
        raise NotImplementedError


class TransformersEmotionProvider(EmotionProvider):
    """Use a small HuggingFace model for emotion classification."""

    _MODEL = "j-hartmann/emotion-english-distilroberta-base"

    def __init__(self) -> None:
        from transformers import pipeline  # type: ignore
        self._pipe = pipeline(
            "text-classification",
            model=self._MODEL,
            top_k=1,
            truncation=True,
        )

    def detect(self, text: str) -> Tuple[str, float]:
        try:
            result = self._pipe(text[:512])
            top = result[0][0] if isinstance(result[0], list) else result[0]
            label = top["label"].lower()
            # Normalise label to our set
            for emotion in EMOTION_LABELS:
                if emotion in label:
                    return emotion, round(top["score"], 3)
            return "neutral", round(top["score"], 3)
        except Exception as exc:
            logger.warning("Transformers emotion detection failed: %s", exc)
            return "neutral", 0.5


class VADEREmotionProvider(EmotionProvider):
    """Sentiment-based emotion using VADER (no model download needed)."""

    def __init__(self) -> None:
        from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer  # type: ignore
        self._analyzer = SentimentIntensityAnalyzer()

    def detect(self, text: str) -> Tuple[str, float]:
        scores = self._analyzer.polarity_scores(text)
        compound = scores["compound"]
        if compound >= 0.5:
            return "happy", round((compound + 1) / 2, 3)
        elif compound >= 0.05:
            return "neutral", 0.6
        elif compound <= -0.5:
            return "angry", round((-compound + 1) / 2, 3)
        elif compound <= -0.05:
            return "sad", round((-compound + 1) / 2, 3)
        return "neutral", 0.5


class HeuristicEmotionProvider(EmotionProvider):
    """Pure keyword matching – zero dependencies."""

    def detect(self, text: str) -> Tuple[str, float]:
        lowered = text.lower()
        for emotion, pattern in _KEYWORD_MAP.items():
            if re.search(pattern, lowered):
                return emotion, 0.6
        return "neutral", 0.5


def get_emotion_provider() -> EmotionProvider:
    engine = os.getenv("EMOTION_ENGINE", "vader").strip().lower()
    if engine == "transformers":
        try:
            provider = TransformersEmotionProvider()
            logger.info("Using Transformers emotion provider")
            return provider
        except Exception as exc:
            logger.warning("Transformers emotion provider unavailable (%s); trying VADER", exc)
    if engine in ("vader", "transformers"):
        try:
            provider = VADEREmotionProvider()
            logger.info("Using VADER emotion provider")
            return provider
        except Exception as exc:
            logger.warning("VADER unavailable (%s); using heuristic fallback", exc)
    logger.info("Using heuristic emotion provider")
    return HeuristicEmotionProvider()
