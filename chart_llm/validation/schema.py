"""Validate a Vega-Lite spec against the official JSON schema."""

import json
from pathlib import Path

import jsonschema

# TODO: bundle vega-lite-schema.json or fetch it from cdn.jsdelivr.net at startup
_SCHEMA_PATH = Path(__file__).parent / "vega-lite-schema.json"


def validate_schema(spec: dict) -> list[str]:
    """Return a list of schema violations, or [] if the spec is valid."""
    # TODO: load schema once at module level, not on every call
    if not _SCHEMA_PATH.exists():
        raise FileNotFoundError(
            f"Vega-Lite schema not found at {_SCHEMA_PATH}. "
            "Run `chart-llm fetch-schema` to download it."
        )
    schema = json.loads(_SCHEMA_PATH.read_text())
    validator = jsonschema.Draft7Validator(schema)
    return [str(e.message) for e in validator.iter_errors(spec)]
