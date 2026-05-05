"""Render a Vega-Lite spec to HTML (always) and optionally PNG (requires node + vega-cli)."""

from pathlib import Path

import altair as alt

# TODO: PNG rendering requires `npm i -g vega-cli` and subprocess call to `vl2png`
# TODO: consider altair_saver as an alternative for PNG


def render_html(spec: dict, output_path: Path) -> None:
    """Write a self-contained HTML file that renders the spec via Vega-Embed."""
    # TODO: embed the spec in a minimal HTML template with vega-embed CDN links
    raise NotImplementedError


def render_png(spec: dict, output_path: Path, scale: float = 2.0) -> None:
    """Render to PNG via vl2png (requires Node.js + vega-cli installed globally)."""
    # TODO: subprocess call to `vl2png --scale {scale}`, pipe spec JSON to stdin
    raise NotImplementedError


def spec_to_altair(spec: dict) -> alt.Chart:
    """Wrap a raw Vega-Lite dict as an Altair Chart for Jupyter display."""
    # TODO: use alt.Chart.from_dict(spec) once we confirm it works with v5 specs
    raise NotImplementedError
