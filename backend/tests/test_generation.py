"""Generation tests use mocked provider clients — never a real API call."""
from unittest.mock import MagicMock, patch

import pytest

from generation.base import build_prompt
from generation.factory import get_generator


def test_build_prompt_includes_question_and_numbered_passages():
    prompt = build_prompt("what is X?", ["passage one", "passage two"])
    assert "what is X?" in prompt
    assert "[1] passage one" in prompt
    assert "[2] passage two" in prompt


def test_build_prompt_handles_no_passages():
    prompt = build_prompt("what is X?", [])
    assert "(none returned)" in prompt


def test_factory_returns_none_when_no_provider_configured(monkeypatch):
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    assert get_generator() is None


def test_factory_picks_openai_when_only_that_key_is_set(monkeypatch):
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "fake-key")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    generator = get_generator()
    assert generator is not None
    assert generator.name == "openai"


def test_factory_picks_gemini_when_only_that_key_is_set(monkeypatch):
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
    generator = get_generator()
    assert generator is not None
    assert generator.name == "gemini"


def test_factory_respects_explicit_llm_provider_override(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    monkeypatch.setenv("OPENAI_API_KEY", "fake-key")
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
    generator = get_generator()
    assert generator.name == "gemini"


def test_openai_generator_calls_chat_completions_with_fixed_prompt(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "fake-key")
    from generation.openai_generator import OpenAIGenerator

    with patch("openai.OpenAI") as mock_openai_cls:
        mock_client = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message.content = "the answer"
        mock_client.chat.completions.create.return_value = MagicMock(choices=[mock_choice])
        mock_openai_cls.return_value = mock_client

        generator = OpenAIGenerator()
        result = generator.generate("what is X?", ["passage one"])

        assert result == "the answer"
        call_kwargs = mock_client.chat.completions.create.call_args.kwargs
        assert "passage one" in call_kwargs["messages"][0]["content"]


def test_gemini_generator_calls_generate_content_with_fixed_prompt(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
    from generation.gemini_generator import GeminiGenerator

    with patch("google.genai.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = MagicMock(text="the answer")
        mock_client_cls.return_value = mock_client

        generator = GeminiGenerator()
        result = generator.generate("what is X?", ["passage one"])

        assert result == "the answer"
        call_kwargs = mock_client.models.generate_content.call_args.kwargs
        assert "passage one" in call_kwargs["contents"]


def test_openai_generator_raises_clearly_without_api_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    from generation.openai_generator import OpenAIGenerator

    with pytest.raises(KeyError):
        OpenAIGenerator()
