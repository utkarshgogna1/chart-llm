"""Evaluation metrics for generated Vega-Lite specs."""

from dataclasses import dataclass

# TODO: define gold-standard answer format (reference spec or human rating)
# TODO: implement field-level accuracy (did the model pick the right columns?)
# TODO: implement chart-type accuracy (bar vs line vs scatter)
# TODO: measure first-pass validity rate vs. with-validation validity rate


@dataclass
class SpecMetrics:
    model_id: str
    question_id: str
    attempt_count: int
    success: bool
    latency_ms: float
    first_pass_valid: bool
    schema_error_count: int
    semantic_error_count: int


def aggregate(results: list[SpecMetrics]) -> dict:
    """Compute summary stats across a benchmark run (validity rate, avg attempts, etc.)."""
    # TODO: group by model_id, compute mean/std for each metric
    raise NotImplementedError
