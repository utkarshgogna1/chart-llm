"""Groq adapter for Llama-3-70B via Groq's OpenAI-compatible REST API."""

import os

import httpx

from chart_llm.models.base import LLMModel, LLMResponse

# Endpoint: https://api.groq.com/openai/v1/chat/completions
# Model: llama3-70b-8192
# Auth: Bearer GROQ_API_KEY


class GroqModel(LLMModel):
    MODEL = "llama3-70b-8192"

    def __init__(self) -> None:
        self._api_key = os.environ["GROQ_API_KEY"]
        self._client = httpx.Client(base_url="https://api.groq.com")

    def generate(self, system: str, user: str, max_retries: int = 2) -> LLMResponse:
        # TODO: implement in next step
        raise NotImplementedError("implemented in next step")
