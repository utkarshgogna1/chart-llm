"""Render validation: catch specs that pass all other validators but fail to render."""

from chart_llm.pipeline.dataset import DatasetContext
from chart_llm.rendering.render import RenderError, render_to_html
from chart_llm.validation.types import ValidationError, ValidationResult


def validate_render(spec: dict, dataset_ctx: DatasetContext) -> ValidationResult:
    """Try to render the spec to HTML; fail if the rendering library raises.

    This is the last and most expensive validation stage — it only runs when
    schema, structural, data_ref, columns, and semantics have all passed.
    Catches specs whose JSON structure is technically valid but that the
    rendering library rejects (invalid transform syntax, unsupported mark
    combinations, etc.).
    """
    try:
        render_to_html(spec, dataset_ctx.df)
        return ValidationResult(ok=True, errors=[])
    except RenderError as exc:
        return ValidationResult(
            ok=False,
            errors=[
                ValidationError(
                    stage="render",
                    code="render_failed",
                    message=str(exc),
                    path="spec",
                    suggestion=None,
                )
            ],
            stage_failed="render",
        )
    except Exception as exc:
        return ValidationResult(
            ok=False,
            errors=[
                ValidationError(
                    stage="render",
                    code="render_failed",
                    message=f"Unexpected rendering error: {exc}",
                    path="spec",
                    suggestion=None,
                )
            ],
            stage_failed="render",
        )
