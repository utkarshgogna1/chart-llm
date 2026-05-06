"""Session-level fixtures shared across test modules."""

import pytest


@pytest.fixture(scope="session")
def vega_lite_schema():
    """Download the Vega-Lite schema once per session if not already cached.

    Tests that require the real schema depend on this fixture. If the network
    is unavailable and the schema is not cached, schema tests are skipped.
    """
    from chart_llm.validation.schema import _CACHE_PATH, fetch_schema

    if not _CACHE_PATH.exists():
        try:
            fetch_schema()
        except Exception as exc:
            pytest.skip(f"Vega-Lite schema unavailable (no cache, no network): {exc}")

    return _CACHE_PATH
