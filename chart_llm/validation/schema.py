"""Validate a Vega-Lite spec against the official JSON Schema (Draft-07)."""

import json
from functools import lru_cache
from pathlib import Path

import httpx
import jsonschema

from chart_llm.validation.types import ValidationError, ValidationResult

_CACHE_DIR = Path(__file__).parent / "_cache"
_CACHE_PATH = _CACHE_DIR / "vega_lite_v5_schema.json"

_VALIDATOR_CODE: dict[str, str] = {
    "required": "required_field_missing",
    "type": "wrong_type",
    "enum": "invalid_enum_value",
    "anyOf": "invalid_value",
    "oneOf": "invalid_value",
    "additionalProperties": "unknown_property",
    "minimum": "value_out_of_range",
    "maximum": "value_out_of_range",
}


def fetch_schema(version: str = "5.20.1") -> Path:
    """Download the Vega-Lite JSON Schema and save to cache. Returns cache path."""
    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    url = f"https://vega.github.io/schema/vega-lite/v{version}.json"
    resp = httpx.get(url, follow_redirects=True, timeout=30)
    resp.raise_for_status()
    _CACHE_PATH.write_text(resp.text, encoding="utf-8")
    _load_schema.cache_clear()
    return _CACHE_PATH


@lru_cache(maxsize=1)
def _load_schema() -> dict:
    if not _CACHE_PATH.exists():
        raise FileNotFoundError(
            f"Vega-Lite schema not found at {_CACHE_PATH}. "
            "Run `chart-llm fetch-schema` to download it."
        )
    return json.loads(_CACHE_PATH.read_text(encoding="utf-8"))


def _make_path(error: jsonschema.ValidationError) -> str:
    if error.absolute_path:
        return "/" + "/".join(str(k) for k in error.absolute_path)
    return "/"


def validate_schema(spec: dict) -> ValidationResult:
    schema = _load_schema()
    validator = jsonschema.Draft7Validator(schema)
    raw_errors = sorted(validator.iter_errors(spec), key=lambda e: e.path)[:5]

    if not raw_errors:
        return ValidationResult(ok=True, errors=[])

    errors = [
        ValidationError(
            stage="schema",
            code=_VALIDATOR_CODE.get(e.validator, "schema_violation"),
            message=e.message,
            path=_make_path(e),
        )
        for e in raw_errors
    ]
    return ValidationResult(ok=False, errors=errors, stage_failed="schema")
