"""Orchestrate all four validators in order, short-circuiting on first failure."""

from chart_llm.pipeline.dataset import DatasetContext
from chart_llm.validation.columns import validate_columns
from chart_llm.validation.data_ref import validate_data_ref
from chart_llm.validation.schema import validate_schema
from chart_llm.validation.semantics import validate_semantics
from chart_llm.validation.types import ValidationResult


def run_validation(
    spec: dict,
    dataset_ctx: DatasetContext,
    expected_data_name: str = "table",
) -> ValidationResult:
    """Run schema → data_ref → columns → semantics, stopping at first failure."""
    for fn in (
        lambda: validate_schema(spec),
        lambda: validate_data_ref(spec, expected_data_name),
        lambda: validate_columns(spec, dataset_ctx),
        lambda: validate_semantics(spec, dataset_ctx),
    ):
        result = fn()
        if not result.ok:
            return result
    return ValidationResult(ok=True, errors=[])
