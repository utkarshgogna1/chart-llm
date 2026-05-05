"""Abstract base class for all LLM model adapters."""

from abc import ABC, abstractmethod

from pydantic import BaseModel


class GenerationRequest(BaseModel):
    system_prompt: str
    user_prompt: str
    temperature: float = 0.2
    max_tokens: int = 2048


class GenerationResponse(BaseModel):
    content: str
    model_id: str
    input_tokens: int | None = None
    output_tokens: int | None = None
    latency_ms: float | None = None


class LLMModel(ABC):
    """Common interface for all LLM backends used in chart-llm."""

    @property
    @abstractmethod
    def model_id(self) -> str:
        """Canonical model identifier used in benchmark results."""
        ...

    @abstractmethod
    async def generate(self, request: GenerationRequest) -> GenerationResponse:
        # TODO: implement in each subclass
        ...
