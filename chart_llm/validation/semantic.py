"""Semantic validation: check that field names and types match the actual CSV."""

import pandas as pd

# TODO: implement checks for:
#   - every encoding.*.field exists as a column in the dataframe
#   - quantitative fields are numeric, ordinal/nominal are categorical
#   - temporal fields are parseable as dates
#   - aggregate functions are only applied to quantitative fields


def validate_semantics(spec: dict, df: pd.DataFrame) -> list[str]:
    """Return a list of semantic errors, or [] if the spec is consistent with df."""
    errors: list[str] = []
    # TODO: walk encoding channels and validate each field reference
    return errors
