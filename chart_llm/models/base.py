"""Abstract base class for all LLM model adapters."""

import json
import re
from abc import ABC, abstractmethod
from typing import Optional

from pydantic import BaseModel, ConfigDict


class LLMResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    text: str
    model_name: str
    latency_ms: float
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    cost_usd: float = 0.0


class LLMModel(ABC):
    """Common interface for all LLM backends used in chart-llm."""

    @abstractmethod
    def generate(self, system: str, user: str, max_retries: int = 2) -> LLMResponse: ...

    @classmethod
    def extract_json(cls, text: str) -> dict:
        """Strip ```json fences and parse JSON, raising ValueError on failure."""
        stripped = text.strip()
        stripped = re.sub(r"^```(?:json)?\s*", "", stripped, flags=re.IGNORECASE)
        stripped = re.sub(r"\s*```$", "", stripped.strip())
        try:
            return json.loads(stripped)
        except json.JSONDecodeError as e:
            raise ValueError(
                f"Failed to parse JSON from model output: {e}\nRaw text: {text!r}"
            ) from e
