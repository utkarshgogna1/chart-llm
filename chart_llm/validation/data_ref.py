"""Validate that the spec references data as {"name": "<expected>"} (not inline)."""

from chart_llm.validation.types import ValidationError, ValidationResult


def validate_data_ref(spec: dict, expected_name: str = "table") -> ValidationResult:
    _ok = ValidationResult(ok=True, errors=[])

    def _fail(code: str, message: str, path: str) -> ValidationResult:
        return ValidationResult(
            ok=False,
            errors=[
                ValidationError(
                    stage="data_ref",
                    code=code,
                    message=message,
                    path=path,
                    suggestion=f'Use "data": {{"name": "{expected_name}"}}',
                )
            ],
            stage_failed="data_ref",
        )

    data = spec.get("data")
    if data is None:
        return _fail("missing_data", 'Spec is missing the required "data" field', "/data")

    if "values" in data:
        return _fail(
            "inline_data",
            "Spec embeds inline data values instead of a named reference",
            "/data",
        )
    if "url" in data:
        return _fail(
            "url_data",
            "Spec references data via URL instead of a named reference",
            "/data",
        )

    name = data.get("name")
    if name != expected_name:
        return _fail(
            "wrong_data_name",
            f'data.name is "{name}", expected "{expected_name}"',
            "/data/name",
        )

    return _ok
