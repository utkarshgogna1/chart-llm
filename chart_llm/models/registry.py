"""Factory for creating LLM clients by name."""

from chart_llm.models.base import LLMModel
from chart_llm.models.gemini import GeminiClient


def get_client(name: str) -> LLMModel:
    """Return a configured LLM client for the given name.

    Supported names: "gemini-flash", "llama-70b-groq", "llama-8b-local".
    """
    if name == "gemini-flash":
        return GeminiClient()
    if name in ("llama-70b-groq", "llama-8b-local"):
        raise NotImplementedError("implemented in next step")
    raise ValueError(f"Unknown model name: {name!r}. Choose from: gemini-flash, llama-70b-groq, llama-8b-local")
