"""Orchestrate all validators in order, short-circuiting on first failure."""

from chart_llm.pipeline.dataset import DatasetContext
from chart_llm.validation.columns import validate_columns
from chart_llm.validation.data_ref import validate_data_ref
from chart_llm.validation.render import validate_render
from chart_llm.validation.schema import validate_schema
from chart_llm.validation.semantics import validate_semantics
from chart_llm.validation.structural import validate_structural
from chart_llm.validation.types import ValidationResult


def run_validation(
    spec: dict,
    dataset_ctx: DatasetContext,
    expected_data_name: str = "table",
    *,
    include_render: bool = False,
) -> ValidationResult:
    """Run schema → structural → data_ref → columns → semantics [→ render], stopping at first failure.

    include_render: if True, add a final render stage that tries to call
    render_to_html on the spec. Default is False because rendering adds
    latency; the eval runner enables it, the interactive retry loop leaves it off.
    """
    stages = [
        lambda: validate_schema(spec),
        lambda: validate_structural(spec),
        lambda: validate_data_ref(spec, expected_data_name),
        lambda: validate_columns(spec, dataset_ctx),
        lambda: validate_semantics(spec, dataset_ctx),
    ]
    if include_render:
        stages.append(lambda: validate_render(spec, dataset_ctx))

    for fn in stages:
        result = fn()
        if not result.ok:
            return result
    return ValidationResult(ok=True, errors=[])
