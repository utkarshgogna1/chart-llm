"""Gemini Flash adapter — direct REST, no Google SDK."""

import os
from typing import Optional

import httpx
from dotenv import load_dotenv

from chart_llm.models._http import post_with_backoff
from chart_llm.models.base import LLMModel, LLMResponse

load_dotenv()

_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"

# Longer default backoff for Gemini free tier, which rate-limits aggressively.
_DEFAULT_RETRY_DELAYS = [5, 15, 45]


class GeminiClient(LLMModel):
    def __init__(
        self,
        model: str = "gemini-2.0-flash",
        *,
        _client: Optional[httpx.Client] = None,
        retry_delays: Optional[list[int]] = None,
    ) -> None:
        self._model = model
        self._api_key = os.environ["GEMINI_API_KEY"]
        self._client = _client or httpx.Client(timeout=60)
        self._retry_delays = (
            retry_delays if retry_delays is not None else _DEFAULT_RETRY_DELAYS
        )

    def generate(self, system: str, user: str, max_retries: int = 2) -> LLMResponse:
        url = f"{_BASE_URL}/{self._model}:generateContent"
        payload = {
            "system_instruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": user}]}],
        }
        resp, latency_ms = post_with_backoff(
            self._client,
            url,
            max_retries,
            retry_delays=self._retry_delays,
            json=payload,
            params={"key": self._api_key},
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
