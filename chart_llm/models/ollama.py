"""Ollama adapter for local Llama-3.1-8B."""

import os
import time

import httpx

from chart_llm.models.base import LLMModel, LLMResponse

_DEFAULT_BASE_URL = "http://localhost:11434"


class OllamaClient(LLMModel):
    def __init__(
        self, model: str = "llama3.1:8b", *, _client: httpx.Client | None = None
    ) -> None:
        self._model = model
        base_url = os.environ.get("OLLAMA_BASE_URL", _DEFAULT_BASE_URL)
        self._client = _client or httpx.Client(base_url=base_url, timeout=120)

    def generate(self, system: str, user: str, max_retries: int = 2) -> LLMResponse:
        payload = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "stream": False,
        }
        try:
            t0 = time.perf_counter()
            resp = self._client.post("/api/chat", json=payload)
            latency_ms = (time.perf_counter() - t0) * 1000
        except httpx.ConnectError:
            raise RuntimeError(
                "Ollama is not running. Install from https://ollama.com and run "
                "`ollama pull llama3.1:8b`."
            )
        if resp.status_code == 404:
            raise RuntimeError(
                f"Ollama model '{self._model}' is not pulled. Run: ollama pull {self._model}"
            )
        resp.raise_for_status()
        data = resp.json()
        text = data["message"]["content"]
        return LLMResponse(
            text=text,
            model_name=self._model,
            latency_ms=latency_ms,
            prompt_tokens=None,
            completion_tokens=None,
        )
