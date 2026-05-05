"""Top-level pipeline: CSV + question → validated Vega-Lite spec."""

from dataclasses import dataclass, field

import pandas as pd

from chart_llm.models.base import LLMModel
from chart_llm.pipeline.retry import retry_until_valid

# TODO: add CSV schema extraction helper (column names, dtypes, sample rows)


@dataclass
class PipelineResult:
    spec: dict
    attempts: int
    validation_errors_per_attempt: list[list[str]] = field(default_factory=list)
    success: bool = True


async def run_pipeline(
    model: LLMModel,
    df: pd.DataFrame,
    question: str,
    max_retries: int = 3,
    validate: bool = True,
) -> PipelineResult:
    """Generate a Vega-Lite spec for `question` over `df`, optionally retrying on errors."""
    # TODO: extract csv_schema string from df
    # TODO: call retry_until_valid when validate=True, else call model once
    raise NotImplementedError
