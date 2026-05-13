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


def _collect_derived_fields(spec: dict) -> set[str]:
    """Return field names produced by any transform that defines an 'as' alias.

    Covers: calculate, window, joinaggregate, aggregate, bin, timeUnit.
    These are valid encoding references even though they are not in the original
    dataset schema — the transform creates them at query time.
    """
    derived: set[str] = set()
    for step in spec.get("transform") or []:
        if not isinstance(step, dict):
            continue
        # calculate / bin / timeUnit — top-level scalar "as"
        if isinstance(step.get("as"), str):
            derived.add(step["as"])
        # window / joinaggregate / aggregate — "as" lives inside each operation object
        for key in ("window", "joinaggregate", "aggregate"):
            for op in step.get(key) or []:
                if isinstance(op, dict) and isinstance(op.get("as"), str):
                    derived.add(op["as"])
    # Handle nested specs (faceted views)
    nested = spec.get("spec")
    if isinstance(nested, dict):
        derived |= _collect_derived_fields(nested)
    return derived


def validate_columns(spec: dict, dataset_ctx: DatasetContext) -> ValidationResult:
    known = {col.name for col in dataset_ctx.column_schema} | _collect_derived_fields(spec)
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
