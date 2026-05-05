"""Gemini Flash adapter — direct REST, no Google SDK."""

import os

import httpx
from dotenv import load_dotenv

from chart_llm.models._http import post_with_backoff
from chart_llm.models.base import LLMModel, LLMResponse

load_dotenv()

_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"


class GeminiClient(LLMModel):
    def __init__(self, model: str = "gemini-2.0-flash", *, _client: httpx.Client | None = None) -> None:
        self._model = model
        self._api_key = os.environ["GEMINI_API_KEY"]
        self._client = _client or httpx.Client(timeout=60)

    def generate(self, system: str, user: str, max_retries: int = 2) -> LLMResponse:
        url = f"{_BASE_URL}/{self._model}:generateContent"
        payload = {
            "system_instruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": user}]}],
        }
        resp, latency_ms = post_with_backoff(
            self._client, url, max_retries, json=payload, params={"key": self._api_key}
        )
        data = resp.json()
        text = data["candidates"][0]["content"]["parts"][0]["text"]
        usage = data.get("usageMetadata", {})
        return LLMResponse(
            text=text,
            model_name=self._model,
            latency_ms=latency_ms,
            prompt_tokens=usage.get("promptTokenCount"),
            completion_tokens=usage.get("candidatesTokenCount"),
        )
