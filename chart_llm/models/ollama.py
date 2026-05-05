"""Ollama adapter for local Llama-3.1-8B."""

import httpx

from chart_llm.models.base import LLMModel, LLMResponse

# Endpoint: http://localhost:11434/api/chat
# Model: llama3.1:8b


class OllamaModel(LLMModel):
    MODEL = "llama3.1:8b"

    def __init__(self, base_url: str = "http://localhost:11434") -> None:
        self._client = httpx.Client(base_url=base_url)

    def generate(self, system: str, user: str, max_retries: int = 2) -> LLMResponse:
        # TODO: implement in next step
        raise NotImplementedError("implemented in next step")
