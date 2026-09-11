"""Local generation through an Ollama server on the user's machine.

This is the generator the target architecture (docs/03) requires: the query
and every decrypted passage stay on the device. It talks HTTP to
localhost:11434 (or OLLAMA_HOST) and never to a third party. Quality is a
function of the local model and is what an answer-quality experiment
measures; nothing here improves it.

Select with LLM_PROVIDER=ollama; OLLAMA_MODEL picks the model (default
llama3.2). If the server is not running, generation fails loudly and the API
reports generation_status "error:...", never a silent fallback to a hosted
provider.
"""
from __future__ import annotations

import json
import os
import urllib.request

from .base import Generator, build_prompt

DEFAULT_MODEL = "llama3.2"
DEFAULT_HOST = "http://localhost:11434"


class OllamaGenerator(Generator):
    name = "ollama"

    def __init__(self, model: str | None = None, host: str | None = None, timeout: float = 120.0) -> None:
        self.model = model or os.environ.get("OLLAMA_MODEL", DEFAULT_MODEL)
        self.host = (host or os.environ.get("OLLAMA_HOST", DEFAULT_HOST)).rstrip("/")
        if not self.host.startswith(("http://localhost", "http://127.0.0.1", "http://[::1]")):
            # A remote host would move the generator out of the trusted zone.
            raise ValueError("OllamaGenerator only talks to a local server; set OLLAMA_HOST to localhost")
        self.timeout = timeout

    def generate(self, question: str, passages: list[str]) -> str:
        body = json.dumps({
            "model": self.model, "prompt": build_prompt(question, passages), "stream": False,
            # Qwen3-family "thinking" traces off: the fixed prompt stays the whole
            # prompt and the response is only the answer. Ignored by models
            # without a thinking mode.
            "think": False,
            "options": {"temperature": 0.0},
        }).encode("utf-8")
        request = urllib.request.Request(f"{self.host}/api/generate", data=body,
                                         headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(request, timeout=self.timeout) as response:  # noqa: S310 - localhost only
            payload = json.loads(response.read().decode("utf-8"))
        return str(payload.get("response", "")).strip()
