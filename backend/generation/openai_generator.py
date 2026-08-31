"""OpenAI-backed generator. Demo/dev only — see backend/generation/base.py."""
from __future__ import annotations

import os

from .base import Generator, build_prompt

DEFAULT_MODEL = "gpt-4o-mini"


class OpenAIGenerator(Generator):
    name = "openai"

    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        from openai import OpenAI  # deferred: don't require the package unless used

        self.model = model or os.environ.get("OPENAI_MODEL", DEFAULT_MODEL)
        self._client = OpenAI(api_key=api_key or os.environ["OPENAI_API_KEY"])

    def generate(self, question: str, passages: list[str]) -> str:
        prompt = build_prompt(question, passages)
        response = self._client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.choices[0].message.content or ""
