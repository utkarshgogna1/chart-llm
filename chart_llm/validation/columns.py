"""Validate that every field reference in the spec exists in the dataset."""

import difflib

from chart_llm.pipeline.dataset import DatasetContext
from chart_llm.validation.types import ValidationError, ValidationResult


def _collect_field_refs(obj: object, path: str = "") -> list[tuple[str, str]]:
    """Walk obj recursively; return (field_value, json_pointer) for every field ref."""
    refs: list[tuple[str, str]] = []
    if isinstance(obj, dict):
        if "field" in obj and isinstance(obj["field"], str):
            refs.append((obj["field"], path))
        for key, val in obj.items():
            refs.extend(_collect_field_refs(val, f"{path}/{key}"))
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            refs.extend(_collect_field_refs(item, f"{path}/{i}"))
    return refs


def validate_columns(spec: dict, dataset_ctx: DatasetContext) -> ValidationResult:
    known = {col.name for col in dataset_ctx.column_schema}
    known_list = sorted(known)
    errors: list[ValidationError] = []

    for field_value, parent_path in _collect_field_refs(spec):
        # Dotted paths like "address.city" → only validate the root name "address"
        check_name = field_value.split(".")[0]
        if check_name in known:
            continue
        matches = difflib.get_close_matches(check_name, known_list, n=1, cutoff=0.6)
        suggestion = f'Did you mean "{matches[0]}"?' if matches else None
        errors.append(
            ValidationError(
                stage="columns",
                code="missing_column",
                message=f'Column "{check_name}" not found in dataset',
                path=f"{parent_path}/field",
                suggestion=suggestion,
            )
        )

    return ValidationResult(
        ok=not errors,
        errors=errors,
        stage_failed="columns" if errors else None,
    )
