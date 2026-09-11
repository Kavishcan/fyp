"""OllamaGenerator: local-only HTTP generation, mocked transport."""
from __future__ import annotations

import io
import json

import pytest

from generation.factory import get_generator
from generation.ollama_generator import OllamaGenerator


class _Resp(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def test_generate_posts_the_fixed_prompt_to_localhost(monkeypatch):
    captured = {}

    def fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        captured["body"] = json.loads(request.data.decode("utf-8"))
        return _Resp(json.dumps({"response": " forty-two "}).encode("utf-8"))

    monkeypatch.setattr("generation.ollama_generator.urllib.request.urlopen", fake_urlopen)
    gen = OllamaGenerator(model="tiny")
    assert gen.generate("what?", ["passage one"]) == "forty-two"
    assert captured["url"] == "http://localhost:11434/api/generate"
    assert captured["body"]["model"] == "tiny" and captured["body"]["stream"] is False
    assert captured["body"]["think"] is False
    assert "passage one" in captured["body"]["prompt"] and "what?" in captured["body"]["prompt"]


def test_remote_host_is_refused():
    with pytest.raises(ValueError):
        OllamaGenerator(host="https://api.example.com")


def test_factory_selects_ollama_by_env(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "ollama")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    assert isinstance(get_generator(), OllamaGenerator)
