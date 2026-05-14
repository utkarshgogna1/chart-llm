"""Pipeline entry points: generate_spec and run_pipeline stub."""

from typing import Optional

from pydantic import BaseModel

from chart_llm.models.base import LLMModel
from chart_llm.pipeline.dataset import DatasetContext
from chart_llm.prompts.vega_lite import build_generation_prompt


class GenerationResult(BaseModel):
    spec: dict
    raw_text: str
    latency_ms: float
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    model_name: str


def generate_spec(
    client: LLMModel,
    dataset_ctx: DatasetContext,
    question: str,
) -> GenerationResult:
    """Call the model once and return the parsed spec with metadata."""
    system, user = build_generation_prompt(dataset_ctx, question)
    response = client.generate(system=system, user=user)
    spec = LLMModel.extract_json(response.text)
    return GenerationResult(
        spec=spec,
        raw_text=response.text,
        latency_ms=response.latency_ms,
        prompt_tokens=response.prompt_tokens,
        completion_tokens=response.completion_tokens,
        model_name=response.model_name,
    )


def run_pipeline(*args, **kwargs):
    # TODO: implement validation + retry loop in Prompt 5/6
    raise NotImplementedError
