"""Structural validation: common Vega-Lite mistakes the JSON schema allows but that are wrong."""

from chart_llm.validation.types import ValidationError, ValidationResult

_FACETING_CHANNELS = {"facet", "row", "column"}
_TOP_LEVEL_TRANSFORM_KEYS = {"filter", "aggregate", "calculate"}


def validate_structural(spec: dict) -> ValidationResult:
    """Catch structurally wrong specs that pass schema validation but are almost always bugs."""
    errors: list[ValidationError] = []

    # (a) Faceting channels inside encoding — they belong at the top level.
    encoding = spec.get("encoding") or {}
    for ch in _FACETING_CHANNELS:
        if ch in encoding:
            errors.append(
                ValidationError(
                    stage="structural",
                    code=f"{ch}_in_encoding",
                    message=(
                        f"'{ch}' was found inside 'encoding', but faceting channels belong "
                        "at the top level of the spec (not inside encoding)."
                    ),
                    path=f"encoding.{ch}",
                    suggestion=(
                        f"Move '{ch}' to the top level of the spec as a peer of 'mark', "
                        "not inside 'encoding'."
                    ),
                )
            )

    # (b, c) Top-level filter / aggregate / calculate — must be inside transform array.
    for key in _TOP_LEVEL_TRANSFORM_KEYS:
        if key in spec:
            errors.append(
                ValidationError(
                    stage="structural",
                    code=f"{key}_at_top_level",
                    message=(
                        f"'{key}' was found at the top level of the spec. "
                        "It must be inside the 'transform' array."
                    ),
                    path=key,
                    suggestion=(
                        f"Wrap it in a transform array: "
                        f'"transform": [{{"\\"{key}\\"": ...}}]'
                    ),
                )
            )

    # Also catch filter nested inside encoding (not inside transform).
    if "filter" in encoding:
        errors.append(
            ValidationError(
                stage="structural",
                code="filter_in_encoding",
                message=(
                    "'filter' was found inside 'encoding'. "
                    "Filters must go in the 'transform' array."
                ),
                path="encoding.filter",
                suggestion=(
                    "Remove 'filter' from 'encoding' and add it to "
                    '"transform": [{"filter": ...}].'
                ),
            )
        )

    # (d) transform must be a list if present.
    if "transform" in spec and not isinstance(spec["transform"], list):
        errors.append(
            ValidationError(
                stage="structural",
                code="transform_not_a_list",
                message=(
                    f"'transform' must be an array, got {type(spec['transform']).__name__!r}."
                ),
                path="transform",
                suggestion='Use "transform": [{"filter": ...}] — always an array of steps.',
            )
        )

    if errors:
        return ValidationResult(ok=False, errors=errors, stage_failed="structural")
    return ValidationResult(ok=True, errors=[])
