"""Tests for the model layer: GeminiClient, LLMModel.extract_json, registry."""

import json
import os
from unittest.mock import patch

import httpx
import pytest

from chart_llm.models.base import LLMModel, LLMResponse
from chart_llm.models.gemini import GeminiClient

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_VALID_GEMINI_BODY = {
    "candidates": [
        {
            "content": {
                "parts": [{"text": '{"ok": true}'}],
                "role": "model",
            }
        }
    ],
    "usageMetadata": {
        "promptTokenCount": 12,
        "candidatesTokenCount": 8,
        "totalTokenCount": 20,
    },
}


def _make_client(handler) -> GeminiClient:
    """Build a GeminiClient wired to a mock httpx transport."""
    transport = httpx.MockTransport(handler)
    http = httpx.Client(transport=transport)
    return GeminiClient(_client=http)


# ---------------------------------------------------------------------------
# (a) Request body construction
# ---------------------------------------------------------------------------


def test_gemini_builds_correct_request_body(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["body"] = json.loads(request.content)
        return httpx.Response(200, json=_VALID_GEMINI_BODY)

    client = _make_client(handler)
    client.generate(system="You are helpful.", user="Say hi.")

    assert "gemini-2.0-flash:generateContent" in captured["url"]
    assert "key=test-key" in captured["url"]
    body = captured["body"]
    assert body["system_instruction"]["parts"][0]["text"] == "You are helpful."
    assert body["contents"][0]["role"] == "user"
    assert body["contents"][0]["parts"][0]["text"] == "Say hi."


# ---------------------------------------------------------------------------
# (b) Response parsing
# ---------------------------------------------------------------------------


def test_gemini_parses_valid_response(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=_VALID_GEMINI_BODY)

    client = _make_client(handler)
    resp = client.generate(system="sys", user="user")

    assert isinstance(resp, LLMResponse)
    assert resp.text == '{"ok": true}'
    assert resp.model_name == "gemini-2.0-flash"
    assert resp.prompt_tokens == 12
    assert resp.completion_tokens == 8
    assert resp.latency_ms >= 0


def test_gemini_response_missing_usage_metadata(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    body = {k: v for k, v in _VALID_GEMINI_BODY.items() if k != "usageMetadata"}

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=body)

    client = _make_client(handler)
    resp = client.generate(system="sys", user="user")
    assert resp.prompt_tokens is None
    assert resp.completion_tokens is None


# ---------------------------------------------------------------------------
# (c) extract_json strips ```json fences
# ---------------------------------------------------------------------------


def test_extract_json_plain():
    assert LLMModel.extract_json('{"ok": true}') == {"ok": True}


def test_extract_json_strips_json_fence():
    text = '```json\n{"ok": true}\n```'
    assert LLMModel.extract_json(text) == {"ok": True}


def test_extract_json_strips_bare_fence():
    text = "```\n{\"ok\": true}\n```"
    assert LLMModel.extract_json(text) == {"ok": True}


def test_extract_json_raises_on_bad_json():
    with pytest.raises(ValueError, match="Failed to parse JSON"):
        LLMModel.extract_json("not json at all")


def test_extract_json_raises_on_fenced_bad_json():
    with pytest.raises(ValueError, match="Failed to parse JSON"):
        LLMModel.extract_json("```json\nbroken{```")


# ---------------------------------------------------------------------------
# (d) 429 triggers retry with backoff
# ---------------------------------------------------------------------------


def test_429_retries_with_backoff_and_succeeds(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    calls = []
    sleep_calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(1)
        if len(calls) == 1:
            return httpx.Response(429, json={"error": {"message": "rate limited"}})
        return httpx.Response(200, json=_VALID_GEMINI_BODY)

    with patch("chart_llm.models.gemini.time.sleep", side_effect=lambda s: sleep_calls.append(s)):
        client = _make_client(handler)
        resp = client.generate(system="sys", user="user", max_retries=2)

    assert len(calls) == 2
    assert sleep_calls == [2]  # first retry sleeps 2s
    assert resp.text == '{"ok": true}'


def test_429_exhausts_all_retries_and_raises(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    sleep_calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, json={"error": {"message": "rate limited"}})

    with patch("chart_llm.models.gemini.time.sleep", side_effect=lambda s: sleep_calls.append(s)):
        client = _make_client(handler)
        with pytest.raises(httpx.HTTPStatusError):
            client.generate(system="sys", user="user", max_retries=2)

    assert sleep_calls == [2, 4]  # two retries → delays 2s and 4s


def test_429_three_retries_uses_8s_delay(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    sleep_calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, json={"error": {"message": "rate limited"}})

    with patch("chart_llm.models.gemini.time.sleep", side_effect=lambda s: sleep_calls.append(s)):
        client = _make_client(handler)
        with pytest.raises(httpx.HTTPStatusError):
            client.generate(system="sys", user="user", max_retries=3)

    assert sleep_calls == [2, 4, 8]


# ---------------------------------------------------------------------------
# Registry smoke test
# ---------------------------------------------------------------------------


def test_registry_unknown_name_raises():
    from chart_llm.models.registry import get_client

    with pytest.raises(ValueError, match="Unknown model name"):
        get_client("nonexistent-model")


def test_registry_unimplemented_raises_not_implemented(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    from chart_llm.models.registry import get_client

    with pytest.raises(NotImplementedError):
        get_client("llama-70b-groq")

    with pytest.raises(NotImplementedError):
        get_client("llama-8b-local")
