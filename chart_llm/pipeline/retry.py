"""Retry-with-validation loop: generate → validate → feedback → repeat."""

import json
from typing import Literal, Optional

from pydantic import BaseModel

from chart_llm.models.base import LLMModel
from chart_llm.pipeline.dataset import DatasetContext
from chart_llm.prompts.vega_lite import build_generation_prompt, build_retry_prompt
from chart_llm.validation.pipeline import run_validation
from chart_llm.validation.types import ValidationError, ValidationResult


class TokenUsage(BaseModel):
    prompt: int = 0
    completion: int = 0
    total: int = 0


class Attempt(BaseModel):
    attempt_number: int
    spec: Optional[dict] = None
    validation: ValidationResult
    latency_ms: float
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    raw_text: str


class ValidatedRun(BaseModel):
    attempts: list[Attempt]
    final_spec: Optional[dict] = None
    succeeded: bool
    total_latency_ms: float
    total_tokens: TokenUsage
    stop_reason: Literal["validated", "max_attempts", "generation_error"]


def _invalid_json_result() -> ValidationResult:
    return ValidationResult(
        ok=False,
        errors=[
            ValidationError(
                stage="schema",
                code="invalid_json",
                message="Model output could not be parsed as JSON",
                path="/",
                suggestion="Ensure the response is a valid JSON object without markdown fences",
            )
        ],
        stage_failed="schema",
    )


def _sum_tokens(attempts: list[Attempt]) -> TokenUsage:
    prompt = sum(a.prompt_tokens or 0 for a in attempts)
    completion = sum(a.completion_tokens or 0 for a in attempts)
    return TokenUsage(prompt=prompt, completion=completion, total=prompt + completion)


def generate_validated_spec(
    client: LLMModel,
    dataset_ctx: DatasetContext,
    question: str,
    max_attempts: int = 3,
    *,
    include_render: bool = False,
) -> ValidatedRun:
    """Generate a spec, validating after each attempt and retrying with feedback."""
    attempts: list[Attempt] = []
    previous_spec_text: Optional[str] = None
    previous_validation: Optional[ValidationResult] = None

    for attempt_num in range(1, max_attempts + 1):
        if attempt_num == 1:
            system, user = build_generation_prompt(dataset_ctx, question)
        else:
            system, user = build_retry_prompt(question, previous_spec_text, previous_validation)

        try:
            response = client.generate(system=system, user=user)
        except Exception:
            return ValidatedRun(
                attempts=attempts,
                final_spec=None,
                succeeded=False,
                total_latency_ms=sum(a.latency_ms for a in attempts),
                total_tokens=_sum_tokens(attempts),
                stop_reason="generation_error",
            )

        try:
            spec = LLMModel.extract_json(response.text)
            val_result = run_validation(spec, dataset_ctx, include_render=include_render)
        except ValueError:
            spec = None
            val_result = _invalid_json_result()

        attempt = Attempt(
            attempt_number=attempt_num,
            spec=spec,
            validation=val_result,
            latency_ms=response.latency_ms,
            prompt_tokens=response.prompt_tokens,
            completion_tokens=response.completion_tokens,
            raw_text=response.text,
        )
        attempts.append(attempt)

        if val_result.ok:
            break

        previous_spec_text = response.text
        previous_validation = val_result

    last = attempts[-1]
    succeeded = last.validation.ok
    return ValidatedRun(
        attempts=attempts,
        final_spec=last.spec if succeeded else None,
        succeeded=succeeded,
        total_latency_ms=sum(a.latency_ms for a in attempts),
        total_tokens=_sum_tokens(attempts),
        stop_reason="validated" if succeeded else "max_attempts",
    )
