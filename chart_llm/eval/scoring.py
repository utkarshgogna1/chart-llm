"""Scoring functions for benchmark evaluation."""

import json
import re
from typing import Optional

import pandas as pd
from pydantic import BaseModel


class CorrectnessScore(BaseModel):
    match: bool
    mismatches: list[str]


class RenderCheck(BaseModel):
    ok: bool
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_ENCODING_KEYS = ("field", "type", "aggregate", "bin", "timeUnit")


def _extract_mark(spec: dict) -> str:
    mark = spec.get("mark", "")
    if isinstance(mark, dict):
        return mark.get("type", "")
    return str(mark)


def _encoding_fingerprint(channel: dict) -> dict:
    return {k: channel[k] for k in _ENCODING_KEYS if k in channel}


def _compare_encoding(predicted_enc: dict, gt_enc: dict) -> list[str]:
    # Only check channels present in ground truth — predicted is allowed to have
    # additional channels (color, tooltip, etc.) that ground truth doesn't constrain.
    # This treats ground-truth channels as a required SUBSET of predicted channels.
    mismatches = []
    for ch_name, gt_ch in gt_enc.items():
        if not isinstance(gt_ch, dict):
            continue
        gt_fp = _encoding_fingerprint(gt_ch)
        pred_ch = predicted_enc.get(ch_name) or {}
        pred_fp = _encoding_fingerprint(pred_ch) if isinstance(pred_ch, dict) else {}
        if gt_fp != pred_fp:
            mismatches.append(
                f"encoding.{ch_name} mismatch: predicted={pred_fp!r}, expected={gt_fp!r}"
            )
    return mismatches


# Filter normalization — Vega-Lite accepts three equivalent forms for equality filters:
#   1. String expression:  "datum.region === 'West'"  or  "datum.region == 'West'"
#   2. Object form:        {"field": "region", "equal": "West"}
# Normalize all to the object form so they compare equal.
_FILTER_RE = re.compile(
    r"datum\.(\w+)\s*===?\s*(?:'([^']*)'|\"([^\"]*)\")"
)


def _normalize_filter(f: object) -> object:
    if isinstance(f, str):
        m = _FILTER_RE.match(f.strip())
        if m:
            field = m.group(1)
            value = m.group(2) if m.group(2) is not None else m.group(3)
            return {"equal": value, "field": field}
    return f


def _normalize_transform_step(step: dict) -> dict:
    if "filter" in step:
        return {"filter": _normalize_filter(step["filter"])}
    return step


def _transform_set(transforms: list) -> set[str]:
    return {json.dumps(_normalize_transform_step(t), sort_keys=True) for t in transforms}


# ---------------------------------------------------------------------------
# Public scoring functions
# ---------------------------------------------------------------------------


def spec_correctness(predicted: dict, ground_truth: dict) -> CorrectnessScore:
    """Compare predicted spec to ground truth on mark, encoding channels, and transforms.

    Encoding comparison: ground-truth channels are treated as a required subset.
    Predicted may have additional channels without penalty.

    Mark must match exactly (bar ≠ line).
    Aggregates must match exactly (sum ≠ mean).
    Transforms are compared after filter-form normalization (=== ≡ == ≡ object form).
    """
    mismatches: list[str] = []

    pred_mark = _extract_mark(predicted)
    gt_mark = _extract_mark(ground_truth)
    if pred_mark != gt_mark:
        mismatches.append(f"mark mismatch: predicted={pred_mark!r}, expected={gt_mark!r}")

    mismatches.extend(
        _compare_encoding(
            predicted.get("encoding") or {},
            ground_truth.get("encoding") or {},
        )
    )

    gt_transforms = ground_truth.get("transform") or []
    if gt_transforms:
        pred_set = _transform_set(predicted.get("transform") or [])
        gt_set = _transform_set(gt_transforms)
        missing = gt_set - pred_set
        extra = pred_set - gt_set
        if missing:
            mismatches.append(f"transform missing steps: {sorted(missing)!r}")
        if extra:
            mismatches.append(f"transform unexpected steps: {sorted(extra)!r}")

    return CorrectnessScore(match=len(mismatches) == 0, mismatches=mismatches)


def _collect_field_refs(obj: object, refs: list[str]) -> None:
    if isinstance(obj, dict):
        if "field" in obj and isinstance(obj["field"], str):
            refs.append(obj["field"].split(".")[0])
        for v in obj.values():
            _collect_field_refs(v, refs)
    elif isinstance(obj, list):
        for item in obj:
            _collect_field_refs(item, refs)


def hallucinated_columns(predicted: dict, dataset_ctx) -> list[str]:
    """Return sorted list of field names in predicted spec not present in the dataset."""
    refs: list[str] = []
    _collect_field_refs(predicted, refs)
    known = {col.name for col in dataset_ctx.column_schema}
    return sorted({ref for ref in refs if ref not in known})


def render_check(spec: dict, df: pd.DataFrame) -> RenderCheck:
    """Try render_to_html; return ok=True if it succeeds, ok=False with error message if not."""
    try:
        from chart_llm.rendering import render_to_html

        render_to_html(spec, df)
        return RenderCheck(ok=True)
    except Exception as exc:
        return RenderCheck(ok=False, error=str(exc))
