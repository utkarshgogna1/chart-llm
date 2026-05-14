"""Prompt builders for Vega-Lite generation and retry-with-feedback."""

from chart_llm.pipeline.dataset import DatasetContext
from chart_llm.prompts.loader import load_feedback_template, load_prompts
from chart_llm.validation.types import ValidationResult


def build_generation_prompt(
    dataset_ctx: DatasetContext, question: str
) -> tuple[str, str]:
    """Return (system, user) for an initial spec generation request."""
    system, user_template = load_prompts()

    header = f"{'name':<20} | {'dtype':<10} | sample_values"
    divider = "-" * 60
    rows = [
        f"{col.name:<20} | {col.dtype:<10} | {', '.join(col.sample_values)}"
        for col in dataset_ctx.column_schema
    ]
    schema_block = "\n".join([header, divider] + rows)

    user = user_template.format(
        DATASET=dataset_ctx.name,
        ROW_COUNT=dataset_ctx.row_count,
        COLUMN_SCHEMA=schema_block,
        QUESTION=question,
    )
    return system, user


def build_retry_prompt(
    question: str,
    previous_spec_text: str,
    validation_result: ValidationResult,
) -> tuple[str, str]:
    """Return (system, user) for a retry request with structured validation feedback."""
    system, _ = load_prompts()
    template = load_feedback_template()

    error_lines: list[str] = []
    for err in validation_result.errors:
        error_lines.append(f"- [{err.stage}] {err.path} — {err.code}: {err.message}")
        if err.suggestion:
            error_lines.append(f"  Suggestion: {err.suggestion}")
    errors_block = "\n".join(error_lines) if error_lines else "(no errors recorded)"

    # Use str.replace to avoid escaping issues with curly braces in the template
    user = (
        template.replace("{QUESTION}", question)
        .replace("{PREVIOUS_SPEC}", previous_spec_text)
        .replace("{VALIDATION_ERRORS}", errors_block)
    )
    return system, user
