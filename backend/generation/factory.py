"""Picks a generator from environment configuration.

Priority: explicit `LLM_PROVIDER` env var ("openai" | "gemini"), else whichever
API key is set (OPENAI_API_KEY checked first, then GEMINI_API_KEY), else None
— generation stays disabled and the API keeps returning `answer: null`.
"""
from __future__ import annotations

import os

from .base import Generator


def get_generator() -> Generator | None:
    provider = os.environ.get("LLM_PROVIDER", "").strip().lower()

    if provider == "openai" or (not provider and os.environ.get("OPENAI_API_KEY")):
        from .openai_generator import OpenAIGenerator

        return OpenAIGenerator()

    if provider == "gemini" or (not provider and os.environ.get("GEMINI_API_KEY")):
        from .gemini_generator import GeminiGenerator

        return GeminiGenerator()

    return None
