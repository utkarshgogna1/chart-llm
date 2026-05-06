"""Prompt builders for Vega-Lite generation and retry-with-feedback."""

from chart_llm.pipeline.dataset import DatasetContext
from chart_llm.prompts.loader import load_prompts


def build_generation_prompt(dataset_ctx: DatasetContext, question: str) -> tuple[str, str]:
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
    dataset_ctx: DatasetContext,
    question: str,
    previous_spec: str,
    validation_errors: list[str],
) -> tuple[str, str]:
    # TODO: implement in Prompt 6
    raise NotImplementedError("Retry prompts are implemented in Prompt 6")
