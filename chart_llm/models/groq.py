"""Groq adapter for Llama-3.3-70B via Groq's OpenAI-compatible REST API."""

import os

import httpx
from dotenv import load_dotenv

from chart_llm.models._http import post_with_backoff
from chart_llm.models.base import LLMModel, LLMResponse

load_dotenv()

_URL = "https://api.groq.com/openai/v1/chat/completions"


class GroqClient(LLMModel):
    def __init__(
        self,
        model: str = "llama-3.3-70b-versatile",
        *,
        _client: httpx.Client | None = None,
    ) -> None:
        self._model = model
        self._api_key = os.environ["GROQ_API_KEY"]
        self._client = _client or httpx.Client(timeout=60)

    def generate(self, system: str, user: str, max_retries: int = 2) -> LLMResponse:
        payload = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        resp, latency_ms = post_with_backoff(
            self._client,
            _URL,
            max_retries,
            json=payload,
            headers={"Authorization": f"Bearer {self._api_key}"},
        )
        data = resp.json()
        text = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})
        return LLMResponse(
            text=text,
            model_name=self._model,
            latency_ms=latency_ms,
            prompt_tokens=usage.get("prompt_tokens"),
            completion_tokens=usage.get("completion_tokens"),
        )
