"""Gemini-backed generator, via the current `google-genai` SDK (the older
`google-generativeai` package is deprecated). Demo/dev only — see
backend/generation/base.py.
"""
from __future__ import annotations

import os

from .base import Generator, build_prompt

DEFAULT_MODEL = "gemini-2.0-flash"


class GeminiGenerator(Generator):
    name = "gemini"

    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        from google import genai  # deferred: don't require the package unless used

        self.model_name = model or os.environ.get("GEMINI_MODEL", DEFAULT_MODEL)
        self._client = genai.Client(api_key=api_key or os.environ["GEMINI_API_KEY"])

    def generate(self, question: str, passages: list[str]) -> str:
        prompt = build_prompt(question, passages)
        response = self._client.models.generate_content(model=self.model_name, contents=prompt)
        return response.text or ""
