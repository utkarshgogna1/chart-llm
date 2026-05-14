"""Tests for chart_llm.rendering."""


import pandas as pd
import pytest

from chart_llm.rendering import (
    RenderError,
    render_to_html,
    render_to_png,
    render_to_svg,
)

_SCHEMA_URL = "https://vega.github.io/schema/vega-lite/v5.json"

_VALID_SPEC = {
    "$schema": _SCHEMA_URL,
    "data": {"name": "table"},
    "mark": "bar",
    "encoding": {
        "x": {"field": "region", "type": "nominal"},
        "y": {"field": "revenue", "aggregate": "sum", "type": "quantitative"},
    },
    "title": "Revenue by region",
}


@pytest.fixture
def df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "region": ["North", "South", "East"],
            "revenue": [1000.0, 2000.0, 3000.0],
        }
    )


# ---------------------------------------------------------------------------
# render_to_html
# ---------------------------------------------------------------------------


def test_render_to_html_returns_string(df):
    html = render_to_html(_VALID_SPEC, df)
    assert isinstance(html, str)


def test_render_to_html_contains_vega_embed(df):
    html = render_to_html(_VALID_SPEC, df)
    assert "vegaEmbed" in html


def test_render_to_html_embeds_data_rows(df):
    html = render_to_html(_VALID_SPEC, df)
    assert "North" in html
    assert "1000" in html


def test_render_to_html_embeds_spec_fields(df):
    html = render_to_html(_VALID_SPEC, df)
    assert "Revenue by region" in html
    assert '"mark": "bar"' in html


def test_render_to_html_uses_datasets_key(df):
    html = render_to_html(_VALID_SPEC, df)
    # The datasets key injects data while preserving data.name reference
    assert '"datasets"' in html
    assert '"table"' in html


def test_render_to_html_custom_data_name(df):
    spec = dict(_VALID_SPEC, data={"name": "mydata"})
    html = render_to_html(spec, df, expected_data_name="mydata")
    assert '"mydata"' in html
    assert "North" in html


def test_render_to_html_does_not_mutate_spec(df):
    import copy

    original = copy.deepcopy(_VALID_SPEC)
    render_to_html(_VALID_SPEC, df)
    assert _VALID_SPEC == original


# ---------------------------------------------------------------------------
# render_to_png — skipped when vl-convert-python is not installed
# ---------------------------------------------------------------------------


def _vl_convert_available() -> bool:
    try:
        import vl_convert  # noqa: F401

        return True
    except ImportError:
        return False


@pytest.mark.skipif(
    not _vl_convert_available(), reason="vl-convert-python not installed"
)
def test_render_to_png_returns_bytes(df):
    data = render_to_png(_VALID_SPEC, df)
    assert isinstance(data, bytes)
    assert len(data) > 0


@pytest.mark.skipif(
    not _vl_convert_available(), reason="vl-convert-python not installed"
)
def test_render_to_png_starts_with_png_magic(df):
    data = render_to_png(_VALID_SPEC, df)
    assert data[:4] == b"\x89PNG"


@pytest.mark.skipif(
    not _vl_convert_available(), reason="vl-convert-python not installed"
)
def test_render_to_png_raises_render_error_on_bad_spec(df):
    bad_spec = {
        "$schema": _SCHEMA_URL,
        "data": {"name": "table"},
        "mark": "not_a_real_mark",
    }
    with pytest.raises(RenderError):
        render_to_png(bad_spec, df)


# ---------------------------------------------------------------------------
# render_to_svg — skipped when vl-convert-python is not installed
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    not _vl_convert_available(), reason="vl-convert-python not installed"
)
def test_render_to_svg_returns_string(df):
    svg = render_to_svg(_VALID_SPEC, df)
    assert isinstance(svg, str)


@pytest.mark.skipif(
    not _vl_convert_available(), reason="vl-convert-python not installed"
)
def test_render_to_svg_is_valid_svg(df):
    svg = render_to_svg(_VALID_SPEC, df)
    assert svg.strip().startswith("<svg") or "<?xml" in svg


# ---------------------------------------------------------------------------
# RenderError import sanity
# ---------------------------------------------------------------------------


def test_render_error_is_exception():
    err = RenderError("something broke")
    assert isinstance(err, Exception)
    assert str(err) == "something broke"
