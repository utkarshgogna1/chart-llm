"""Tests for the model layer: all three LLM clients, extract_json, registry."""

import json
from unittest.mock import MagicMock, patch

import httpx
import pytest

from chart_llm.models.base import LLMModel, LLMResponse
from chart_llm.models.gemini import GeminiClient
from chart_llm.models.groq import GroqClient
from chart_llm.models.ollama import OllamaClient

# ---------------------------------------------------------------------------
# Shared fixture data
# ---------------------------------------------------------------------------

_VALID_GEMINI_BODY = {
    "candidates": [
        {"content": {"parts": [{"text": '{"ok": true}'}], "role": "model"}}
    ],
    "usageMetadata": {
        "promptTokenCount": 12,
        "candidatesTokenCount": 8,
        "totalTokenCount": 20,
    },
}

_VALID_GROQ_BODY = {
    "choices": [{"message": {"role": "assistant", "content": '{"ok": true}'}}],
    "usage": {"prompt_tokens": 15, "completion_tokens": 7, "total_tokens": 22},
}

_VALID_OLLAMA_BODY = {
    "message": {"role": "assistant", "content": '{"ok": true}'},
    "done": True,
}


def _make_gemini(handler) -> GeminiClient:
    return GeminiClient(_client=httpx.Client(transport=httpx.MockTransport(handler)))


def _make_groq(handler) -> GroqClient:
    return GroqClient(_client=httpx.Client(transport=httpx.MockTransport(handler)))


def _make_ollama(handler) -> OllamaClient:
    http = httpx.Client(base_url="http://localhost:11434", transport=httpx.MockTransport(handler))
    return OllamaClient(_client=http)


# ===========================================================================
# GeminiClient
# ===========================================================================


class TestGeminiRequestBody:
    def test_url_and_key_param(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "test-key")
        captured = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["url"] = str(request.url)
            captured["body"] = json.loads(request.content)
            return httpx.Response(200, json=_VALID_GEMINI_BODY)

        _make_gemini(handler).generate(system="You are helpful.", user="Say hi.")

        assert "gemini-2.0-flash:generateContent" in captured["url"]
        assert "key=test-key" in captured["url"]

    def test_system_and_user_content(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "test-key")
        captured = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["body"] = json.loads(request.content)
            return httpx.Response(200, json=_VALID_GEMINI_BODY)

        _make_gemini(handler).generate(system="sys prompt", user="user prompt")

        body = captured["body"]
        assert body["system_instruction"]["parts"][0]["text"] == "sys prompt"
        assert body["contents"][0]["role"] == "user"
        assert body["contents"][0]["parts"][0]["text"] == "user prompt"


class TestGeminiResponseParsing:
    def test_parses_valid_response(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "test-key")
        resp = _make_gemini(lambda r: httpx.Response(200, json=_VALID_GEMINI_BODY)).generate("s", "u")
        assert isinstance(resp, LLMResponse)
        assert resp.text == '{"ok": true}'
        assert resp.model_name == "gemini-2.0-flash"
        assert resp.prompt_tokens == 12
        assert resp.completion_tokens == 8
        assert resp.latency_ms >= 0

    def test_missing_usage_metadata(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "test-key")
        body = {k: v for k, v in _VALID_GEMINI_BODY.items() if k != "usageMetadata"}
        resp = _make_gemini(lambda r: httpx.Response(200, json=body)).generate("s", "u")
        assert resp.prompt_tokens is None
        assert resp.completion_tokens is None


class TestGemini429Retry:
    def test_retries_on_429_and_succeeds(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "test-key")
        calls, sleeps = [], []

        def handler(request: httpx.Request) -> httpx.Response:
            calls.append(1)
            return (
                httpx.Response(429, json={"error": "rate limited"})
                if len(calls) == 1
                else httpx.Response(200, json=_VALID_GEMINI_BODY)
            )

        with patch("chart_llm.models._http.time.sleep", side_effect=sleeps.append):
            resp = _make_gemini(handler).generate("s", "u", max_retries=2)

        assert len(calls) == 2
        assert sleeps == [2]
        assert resp.text == '{"ok": true}'

    def test_exhausts_retries_and_raises(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "test-key")
        sleeps = []

        with patch("chart_llm.models._http.time.sleep", side_effect=sleeps.append):
            with pytest.raises(httpx.HTTPStatusError):
                _make_gemini(lambda r: httpx.Response(429, json={})).generate("s", "u", max_retries=2)

        assert sleeps == [2, 4]

    def test_three_retries_uses_8s(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "test-key")
        sleeps = []

        with patch("chart_llm.models._http.time.sleep", side_effect=sleeps.append):
            with pytest.raises(httpx.HTTPStatusError):
                _make_gemini(lambda r: httpx.Response(429, json={})).generate("s", "u", max_retries=3)

        assert sleeps == [2, 4, 8]


# ===========================================================================
# LLMModel.extract_json
# ===========================================================================


class TestExtractJson:
    def test_plain_json(self):
        assert LLMModel.extract_json('{"ok": true}') == {"ok": True}

    def test_strips_json_fence(self):
        assert LLMModel.extract_json('```json\n{"ok": true}\n```') == {"ok": True}

    def test_strips_bare_fence(self):
        assert LLMModel.extract_json('```\n{"ok": true}\n```') == {"ok": True}

    def test_raises_on_bad_json(self):
        with pytest.raises(ValueError, match="Failed to parse JSON"):
            LLMModel.extract_json("not json at all")

    def test_raises_on_fenced_bad_json(self):
        with pytest.raises(ValueError, match="Failed to parse JSON"):
            LLMModel.extract_json("```json\nbroken{```")


# ===========================================================================
# GroqClient
# ===========================================================================


class TestGroqRequestBody:
    def test_url_and_auth_header(self, monkeypatch):
        monkeypatch.setenv("GROQ_API_KEY", "groq-key")
        captured = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["url"] = str(request.url)
            captured["auth"] = request.headers.get("authorization", "")
            captured["body"] = json.loads(request.content)
            return httpx.Response(200, json=_VALID_GROQ_BODY)

        _make_groq(handler).generate(system="sys", user="usr")

        assert "groq.com" in captured["url"]
        assert "chat/completions" in captured["url"]
        assert captured["auth"] == "Bearer groq-key"

    def test_messages_format(self, monkeypatch):
        monkeypatch.setenv("GROQ_API_KEY", "groq-key")
        captured = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["body"] = json.loads(request.content)
            return httpx.Response(200, json=_VALID_GROQ_BODY)

        _make_groq(handler).generate(system="system msg", user="user msg")

        body = captured["body"]
        assert body["model"] == "llama-3.3-70b-versatile"
        assert body["messages"][0] == {"role": "system", "content": "system msg"}
        assert body["messages"][1] == {"role": "user", "content": "user msg"}


class TestGroqResponseParsing:
    def test_parses_valid_response(self, monkeypatch):
        monkeypatch.setenv("GROQ_API_KEY", "groq-key")
        resp = _make_groq(lambda r: httpx.Response(200, json=_VALID_GROQ_BODY)).generate("s", "u")
        assert isinstance(resp, LLMResponse)
        assert resp.text == '{"ok": true}'
        assert resp.model_name == "llama-3.3-70b-versatile"
        assert resp.prompt_tokens == 15
        assert resp.completion_tokens == 7
        assert resp.latency_ms >= 0

    def test_missing_usage(self, monkeypatch):
        monkeypatch.setenv("GROQ_API_KEY", "groq-key")
        body = {k: v for k, v in _VALID_GROQ_BODY.items() if k != "usage"}
        resp = _make_groq(lambda r: httpx.Response(200, json=body)).generate("s", "u")
        assert resp.prompt_tokens is None
        assert resp.completion_tokens is None


class TestGroq429Retry:
    def test_retries_on_429_and_succeeds(self, monkeypatch):
        monkeypatch.setenv("GROQ_API_KEY", "groq-key")
        calls, sleeps = [], []

        def handler(request: httpx.Request) -> httpx.Response:
            calls.append(1)
            return (
                httpx.Response(429, json={"error": "rate limited"})
                if len(calls) == 1
                else httpx.Response(200, json=_VALID_GROQ_BODY)
            )

        with patch("chart_llm.models._http.time.sleep", side_effect=sleeps.append):
            resp = _make_groq(handler).generate("s", "u", max_retries=2)

        assert len(calls) == 2
        assert sleeps == [2]
        assert resp.text == '{"ok": true}'

    def test_exhausts_retries_and_raises(self, monkeypatch):
        monkeypatch.setenv("GROQ_API_KEY", "groq-key")
        sleeps = []

        with patch("chart_llm.models._http.time.sleep", side_effect=sleeps.append):
            with pytest.raises(httpx.HTTPStatusError):
                _make_groq(lambda r: httpx.Response(429, json={})).generate("s", "u", max_retries=2)

        assert sleeps == [2, 4]


# ===========================================================================
# OllamaClient
# ===========================================================================


class TestOllamaRequestBody:
    def test_endpoint_and_stream_false(self):
        captured = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["path"] = request.url.path
            captured["body"] = json.loads(request.content)
            return httpx.Response(200, json=_VALID_OLLAMA_BODY)

        _make_ollama(handler).generate(system="sys", user="usr")

        assert captured["path"] == "/api/chat"
        body = captured["body"]
        assert body["stream"] is False
        assert body["model"] == "llama3.1:8b"

    def test_messages_format(self):
        captured = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["body"] = json.loads(request.content)
            return httpx.Response(200, json=_VALID_OLLAMA_BODY)

        _make_ollama(handler).generate(system="system msg", user="user msg")

        msgs = captured["body"]["messages"]
        assert msgs[0] == {"role": "system", "content": "system msg"}
        assert msgs[1] == {"role": "user", "content": "user msg"}


class TestOllamaResponseParsing:
    def test_parses_valid_response(self):
        resp = _make_ollama(lambda r: httpx.Response(200, json=_VALID_OLLAMA_BODY)).generate("s", "u")
        assert isinstance(resp, LLMResponse)
        assert resp.text == '{"ok": true}'
        assert resp.model_name == "llama3.1:8b"
        assert resp.prompt_tokens is None
        assert resp.completion_tokens is None
        assert resp.latency_ms >= 0


class TestOllamaErrors:
    def test_connect_error_raises_helpful_runtime_error(self):
        mock_http = MagicMock()
        mock_http.post.side_effect = httpx.ConnectError("Connection refused")
        client = OllamaClient(_client=mock_http)

        with pytest.raises(RuntimeError, match="Ollama is not running"):
            client.generate(system="s", user="u")

    def test_connect_error_message_includes_install_url(self):
        mock_http = MagicMock()
        mock_http.post.side_effect = httpx.ConnectError("Connection refused")
        client = OllamaClient(_client=mock_http)

        with pytest.raises(RuntimeError, match="https://ollama.com"):
            client.generate(system="s", user="u")

    def test_connect_error_message_includes_pull_command(self):
        mock_http = MagicMock()
        mock_http.post.side_effect = httpx.ConnectError("Connection refused")
        client = OllamaClient(_client=mock_http)

        with pytest.raises(RuntimeError, match="ollama pull llama3.1:8b"):
            client.generate(system="s", user="u")

    def test_404_raises_helpful_runtime_error(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(404, json={"error": "model not found"})

        with pytest.raises(RuntimeError, match="is not pulled"):
            _make_ollama(handler).generate(system="s", user="u")

    def test_404_message_includes_model_name_and_pull_command(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(404, json={"error": "model not found"})

        with pytest.raises(RuntimeError, match=r"ollama pull llama3\.1:8b"):
            _make_ollama(handler).generate(system="s", user="u")


# ===========================================================================
# Registry
# ===========================================================================


class TestRegistry:
    def test_unknown_name_raises_value_error(self):
        from chart_llm.models.registry import get_client

        with pytest.raises(ValueError, match="Unknown model name"):
            get_client("nonexistent-model")

    def test_returns_correct_client_types(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "test-key")
        monkeypatch.setenv("GROQ_API_KEY", "test-key")
        from chart_llm.models.registry import get_client

        assert isinstance(get_client("gemini-flash"), GeminiClient)
        assert isinstance(get_client("llama-70b-groq"), GroqClient)
        assert isinstance(get_client("llama-8b-local"), OllamaClient)
