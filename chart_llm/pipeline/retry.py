"""Retry loop: re-prompts the model with validation feedback until spec is valid."""

import json

import pandas as pd

from chart_llm.models.base import GenerationRequest, LLMModel
from chart_llm.prompts.vega_lite import build_generation_prompt, build_retry_prompt
from chart_llm.validation import validate_schema, validate_semantics

# TODO: consider exponential back-off for rate-limited APIs


async def retry_until_valid(
    model: LLMModel,
    csv_schema: str,
    df: pd.DataFrame,
    question: str,
    max_retries: int = 3,
) -> tuple[dict, list[list[str]]]:
    """
    Attempt to generate a valid spec, retrying up to max_retries times.
    Returns (spec, errors_per_attempt). Raises ValueError if never valid.
    """
    errors_per_attempt: list[list[str]] = []
    previous_spec: str | None = None
    previous_errors: list[str] = []

    for attempt in range(max_retries + 1):
        if attempt == 0:
            prompt = build_generation_prompt(csv_schema, question)
        else:
            prompt = build_retry_prompt(csv_schema, question, previous_spec, previous_errors)

        # TODO: parse JSON robustly (strip markdown fences, handle partial JSON)
        response = await model.generate(
            GenerationRequest(system_prompt="", user_prompt=prompt)
        )
        spec = json.loads(response.content)

        schema_errors = validate_schema(spec)
        semantic_errors = validate_semantics(spec, df)
        all_errors = schema_errors + semantic_errors
        errors_per_attempt.append(all_errors)

        if not all_errors:
            return spec, errors_per_attempt

        previous_spec = response.content
        previous_errors = all_errors

    raise ValueError(f"Spec invalid after {max_retries} retries: {errors_per_attempt[-1]}")
