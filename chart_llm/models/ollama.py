"""Ollama adapter for local Llama-3.1-8B."""

import httpx

from chart_llm.models.base import GenerationRequest, GenerationResponse, LLMModel

# TODO: implement Ollama /api/chat call
# Default base URL: http://localhost:11434
# Model: llama3.1:8b


class OllamaModel(LLMModel):
    MODEL = "llama3.1:8b"

    def __init__(self, base_url: str = "http://localhost:11434") -> None:
        self._client = httpx.AsyncClient(base_url=base_url)

    @property
    def model_id(self) -> str:
        return self.MODEL

    async def generate(self, request: GenerationRequest) -> GenerationResponse:
        # TODO: call /api/chat with stream=False, parse response
        raise NotImplementedError
