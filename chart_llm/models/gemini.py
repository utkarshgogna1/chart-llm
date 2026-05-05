"""Gemini Flash adapter via Google's REST API."""

import os

import httpx

from chart_llm.models.base import GenerationRequest, GenerationResponse, LLMModel

# TODO: implement full Gemini Flash REST call
# Endpoint: https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent
# Auth: ?key=GEMINI_API_KEY


class GeminiModel(LLMModel):
    MODEL = "gemini-2.0-flash"

    def __init__(self) -> None:
        self._api_key = os.environ["GEMINI_API_KEY"]
        self._client = httpx.AsyncClient()

    @property
    def model_id(self) -> str:
        return self.MODEL

    async def generate(self, request: GenerationRequest) -> GenerationResponse:
        # TODO: build request body, call API, parse response
        raise NotImplementedError
