"""LLM providers: OpenAI and Mock fallback."""
from __future__ import annotations

import os
import logging
from typing import List

logger = logging.getLogger(__name__)


class LLMProvider:
    def generate(self, user_message: str, context_snippets: List[str]) -> str:  # noqa: D102
        raise NotImplementedError


class OpenAIProvider(LLMProvider):
    def __init__(self, api_key: str, model: str = "gpt-3.5-turbo") -> None:
        from openai import OpenAI  # lazy import so missing package is survivable
        self._client = OpenAI(api_key=api_key)
        self._model = model

    def generate(self, user_message: str, context_snippets: List[str]) -> str:
        system = (
            "You are a helpful, emotionally intelligent AI avatar. "
            "Use the provided web-search context when relevant, and cite it naturally. "
            "Keep answers concise (2-4 sentences)."
        )
        context_block = "\n\n".join(context_snippets) if context_snippets else ""
        messages = [{"role": "system", "content": system}]
        if context_block:
            messages.append(
                {"role": "user", "content": f"Context from web search:\n{context_block}"}
            )
        messages.append({"role": "user", "content": user_message})

        try:
            resp = self._client.chat.completions.create(
                model=self._model,
                messages=messages,  # type: ignore[arg-type]
                max_tokens=300,
                temperature=0.7,
            )
            return resp.choices[0].message.content.strip()
        except Exception as exc:
            logger.error("OpenAI call failed: %s", exc)
            raise


class MockLLMProvider(LLMProvider):
    """Deterministic fallback when no API key is available."""

    def generate(self, user_message: str, context_snippets: List[str]) -> str:
        if context_snippets:
            snippet_preview = context_snippets[0][:200]
            return (
                f"[Demo mode – no LLM key] "
                f"You asked: \"{user_message}\". "
                f"Based on web search: {snippet_preview}… "
                "Set OPENAI_API_KEY in .env to enable real AI responses."
            )
        return (
            f"[Demo mode – no LLM key] "
            f"You asked: \"{user_message}\". "
            "No search results were found either. "
            "Set OPENAI_API_KEY in .env to enable real AI responses."
        )


def get_llm_provider() -> LLMProvider:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    model = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo").strip()
    if api_key:
        logger.info("Using OpenAI LLM provider (model=%s)", model)
        try:
            return OpenAIProvider(api_key, model)
        except ImportError:
            logger.warning("openai package not installed; falling back to MockLLM")
    logger.info("Using MockLLM provider (no OPENAI_API_KEY set)")
    return MockLLMProvider()
