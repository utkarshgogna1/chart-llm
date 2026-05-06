"""Render a Vega-Lite spec + DataFrame to HTML, PNG, or SVG."""

import copy
import json

import pandas as pd


class RenderError(Exception):
    """Raised when Vega-Lite rendering fails."""


def _inject_data(spec: dict, df: pd.DataFrame, expected_data_name: str) -> dict:
    """Return a deep copy of spec with df rows added as a named dataset.

    Uses the Vega-Lite top-level ``datasets`` key so the original
    ``"data": {"name": ...}`` reference is preserved and the spec stays readable.
    """
    out = copy.deepcopy(spec)
    out["datasets"] = {expected_data_name: df.to_dict(orient="records")}
    return out


_HTML_TEMPLATE = """\
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>chart-llm</title>
  <script src="https://cdn.jsdelivr.net/npm/vega@5"></script>
  <script src="https://cdn.jsdelivr.net/npm/vega-lite@5"></script>
  <script src="https://cdn.jsdelivr.net/npm/vega-embed@6"></script>
  <style>body {{ margin: 24px; font-family: sans-serif; }}</style>
</head>
<body>
  <div id="chart"></div>
  <script>
    const spec = {spec_json};
    vegaEmbed("#chart", spec, {{renderer: "canvas", actions: true}})
      .catch(console.error);
  </script>
</body>
</html>"""


def render_to_html(
    spec: dict,
    df: pd.DataFrame,
    expected_data_name: str = "table",
) -> str:
    """Return a self-contained HTML string that renders the chart in a browser."""
    spec_with_data = _inject_data(spec, df, expected_data_name)
    spec_json = json.dumps(spec_with_data, indent=2)
    return _HTML_TEMPLATE.format(spec_json=spec_json)


def render_to_png(
    spec: dict,
    df: pd.DataFrame,
    expected_data_name: str = "table",
    scale: float = 2.0,
) -> bytes:
    """Return PNG bytes for the chart (pure-Rust via vl-convert, no Node.js needed)."""
    try:
        import vl_convert as vlc
    except ImportError as exc:
        raise RenderError("vl-convert-python is not installed") from exc

    spec_with_data = _inject_data(spec, df, expected_data_name)
    try:
        return vlc.vegalite_to_png(json.dumps(spec_with_data), scale=scale)
    except Exception as exc:
        raise RenderError(f"PNG rendering failed: {exc}") from exc


def render_to_svg(
    spec: dict,
    df: pd.DataFrame,
    expected_data_name: str = "table",
) -> str:
    """Return an SVG string for the chart."""
    try:
        import vl_convert as vlc
    except ImportError as exc:
        raise RenderError("vl-convert-python is not installed") from exc

    spec_with_data = _inject_data(spec, df, expected_data_name)
    try:
        return vlc.vegalite_to_svg(json.dumps(spec_with_data))
    except Exception as exc:
        raise RenderError(f"SVG rendering failed: {exc}") from exc
