"""Groq adapter for Llama-3-70B via Groq's OpenAI-compatible REST API."""

import os

import httpx

from chart_llm.models.base import GenerationRequest, GenerationResponse, LLMModel

# TODO: implement Groq chat completions call
# Endpoint: https://api.groq.com/openai/v1/chat/completions
# Model: llama3-70b-8192
# Auth: Bearer GROQ_API_KEY


class GroqModel(LLMModel):
    MODEL = "llama3-70b-8192"

    def __init__(self) -> None:
        self._api_key = os.environ["GROQ_API_KEY"]
        self._client = httpx.AsyncClient(base_url="https://api.groq.com")

    @property
    def model_id(self) -> str:
        return self.MODEL

    async def generate(self, request: GenerationRequest) -> GenerationResponse:
        # TODO: build OpenAI-compatible chat payload, call API, parse response
        raise NotImplementedError
