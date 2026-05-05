"""Gemini Flash adapter — direct REST, no Google SDK."""

import os
import time

import httpx
from dotenv import load_dotenv

from chart_llm.models.base import LLMModel, LLMResponse

load_dotenv()

_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"
_BACKOFF_DELAYS = [2, 4, 8]


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
        params = {"key": self._api_key}

        last_exc: Exception | None = None
        for attempt in range(max_retries + 1):
            if attempt > 0:
                delay = _BACKOFF_DELAYS[min(attempt - 1, len(_BACKOFF_DELAYS) - 1)]
                time.sleep(delay)

            t0 = time.perf_counter()
            resp = self._client.post(url, json=payload, params=params)
            latency_ms = (time.perf_counter() - t0) * 1000

            if resp.status_code == 429:
                last_exc = httpx.HTTPStatusError(
                    f"Rate limited (429) on attempt {attempt + 1}",
                    request=resp.request,
                    response=resp,
                )
                continue

            resp.raise_for_status()
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

        raise last_exc  # type: ignore[misc]
