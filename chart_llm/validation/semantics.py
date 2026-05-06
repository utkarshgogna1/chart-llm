"""Validate encoding type/aggregate choices against actual column dtypes."""

import pandas as pd

from chart_llm.pipeline.dataset import ColumnInfo, DatasetContext
from chart_llm.validation.types import ValidationError, ValidationResult


def _is_numeric(dtype: str) -> bool:
    return dtype.startswith(("int", "float", "uint"))


def _is_temporal(col: ColumnInfo) -> bool:
    if col.dtype.startswith("datetime"):
        return True
    samples = [v for v in col.sample_values if v]
    if not samples:
        return False
    try:
        pd.to_datetime(samples[:3], format="mixed", errors="raise")
        return True
    except (ValueError, TypeError):
        return False


def _collect_encodings(obj: dict, path: str = "") -> list[tuple[dict, str]]:
    """Walk spec; return (channel_dict, json_pointer) for every encoding channel."""
    results: list[tuple[dict, str]] = []
    if not isinstance(obj, dict):
        return results
    if "encoding" in obj and isinstance(obj["encoding"], dict):
        enc_path = f"{path}/encoding"
        for channel, defn in obj["encoding"].items():
            if isinstance(defn, dict):
                results.append((defn, f"{enc_path}/{channel}"))
    for key in ("spec", "layer", "hconcat", "vconcat", "concat"):
        val = obj.get(key)
        if val is None:
            continue
        sub_path = f"{path}/{key}"
        if isinstance(val, list):
            for i, item in enumerate(val):
                results.extend(_collect_encodings(item, f"{sub_path}/{i}"))
        elif isinstance(val, dict):
            results.extend(_collect_encodings(val, sub_path))
    return results


def validate_semantics(spec: dict, dataset_ctx: DatasetContext) -> ValidationResult:
    col_map = {col.name: col for col in dataset_ctx.column_schema}
    errors: list[ValidationError] = []

    for channel_def, path in _collect_encodings(spec):
        field_value = channel_def.get("field")
        vl_type = channel_def.get("type")
        aggregate = channel_def.get("aggregate")

        if not field_value or not isinstance(field_value, str):
            continue  # count-without-field and similar are fine

        col = col_map.get(field_value.split(".")[0])
        if col is None:
            continue  # column validator owns this error

        if vl_type == "quantitative" and not _is_numeric(col.dtype):
            errors.append(
                ValidationError(
                    stage="semantics",
                    code="non_numeric_quantitative",
                    message=(
                        f'Field "{field_value}" has dtype "{col.dtype}" '
                        f"but is encoded as quantitative"
                    ),
                    path=f"{path}/type",
                    suggestion='Use "nominal" or "ordinal" for string/categorical columns',
                )
            )

        if vl_type == "temporal" and not _is_temporal(col):
            errors.append(
                ValidationError(
                    stage="semantics",
                    code="non_temporal_temporal",
                    message=(
                        f'Field "{field_value}" (dtype "{col.dtype}") does not '
                        f"appear to contain datetime values"
                    ),
                    path=f"{path}/type",
                    suggestion="Check that the column holds ISO-8601 date strings or a datetime dtype",
                )
            )

        if aggregate and aggregate != "count" and not _is_numeric(col.dtype):
            errors.append(
                ValidationError(
                    stage="semantics",
                    code="non_numeric_aggregate",
                    message=(
                        f'Cannot apply aggregate "{aggregate}" to field '
                        f'"{field_value}" with dtype "{col.dtype}"'
                    ),
                    path=f"{path}/aggregate",
                    suggestion="Only sum/mean/min/max/median make sense on numeric fields",
                )
            )

    return ValidationResult(
        ok=not errors,
        errors=errors,
        stage_failed="semantics" if errors else None,
    )
