"""Streamlit demo app for chart-llm."""

import json
import tempfile
from pathlib import Path

import streamlit as st

st.set_page_config(page_title="chart-llm", page_icon="📊", layout="wide")

st.title("📊 chart-llm")
st.caption("Natural-language → Vega-Lite chart generation with LLM validation.")

# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.header("Settings")

    uploaded = st.file_uploader("Upload a CSV file", type=["csv"])

    model_name = st.selectbox(
        "Model",
        ["gemini-flash", "llama-70b-groq", "llama-8b-local"],
        help="gemini-flash requires GEMINI_API_KEY; llama-70b-groq requires GROQ_API_KEY; "
             "llama-8b-local requires Ollama running locally.",
    )

    validate = st.toggle("Enable validation + retry loop", value=True)

    max_attempts = st.slider(
        "Max retry attempts",
        min_value=1, max_value=5, value=3,
        disabled=not validate,
    )

    st.divider()
    st.caption(
        "Set API keys via environment variables or a `.env` file: "
        "`GEMINI_API_KEY`, `GROQ_API_KEY`."
    )

# ── Main area ─────────────────────────────────────────────────────────────────

if uploaded is None:
    st.info("Upload a CSV file in the sidebar to get started.")
    st.stop()

# Load CSV into a temp file so build_dataset_context can work with a Path.
with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tmp:
    tmp.write(uploaded.read())
    tmp_path = Path(tmp.name)

from chart_llm.pipeline.dataset import build_dataset_context  # noqa: E402

try:
    dataset_ctx = build_dataset_context(tmp_path)
except Exception as exc:
    st.error(f"Failed to load CSV: {exc}")
    st.stop()

# Dataset preview
with st.expander("Dataset preview", expanded=False):
    st.dataframe(dataset_ctx.df.head(20), use_container_width=True)
    cols = {c.name: {"dtype": c.dtype, "unique": c.n_unique, "null": c.n_null}
            for c in dataset_ctx.column_schema}
    st.json(cols)

# Question input
question = st.text_input(
    "Ask a question about your data",
    placeholder='e.g. "Show total revenue by region as a bar chart"',
)

if not question:
    st.stop()

generate_btn = st.button("Generate chart", type="primary")
if not generate_btn:
    st.stop()

# ── Generation ────────────────────────────────────────────────────────────────

from chart_llm.models.registry import get_client  # noqa: E402

try:
    client = get_client(model_name)
except Exception as exc:
    st.error(f"Could not initialise model `{model_name}`: {exc}")
    st.stop()

if validate:
    from chart_llm.pipeline.retry import generate_validated_spec  # noqa: E402

    with st.spinner(f"Generating with {model_name} (validation on)…"):
        run = generate_validated_spec(client, dataset_ctx, question, max_attempts=max_attempts)

    # Per-attempt expanders
    for attempt in run.attempts:
        val = attempt.validation
        icon = "✅" if val.ok else "❌"
        label = f"{icon} Attempt {attempt.attempt_number} — {'passed' if val.ok else f'failed at {val.stage_failed}'}"
        with st.expander(label, expanded=not val.ok):
            if val.ok:
                st.success("All validation checks passed.")
            else:
                for err in val.errors:
                    st.error(f"**[{err.code}]** `{err.path}` — {err.message}"
                             + (f"\n\n*Suggestion: {err.suggestion}*" if err.suggestion else ""))
            if attempt.spec:
                st.json(attempt.spec)
            else:
                st.code(attempt.raw_text or "(no output)", language=None)

    # Summary metrics
    tok = run.total_tokens
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Attempts", len(run.attempts))
    c2.metric("Latency", f"{run.total_latency_ms:.0f} ms")
    c3.metric("Tokens", f"{tok.total:,}" if tok.total else "n/a")
    c4.metric("Stop reason", run.stop_reason)

    if not run.succeeded:
        st.error(f"Generation failed after {len(run.attempts)} attempt(s). Try a different question or increase max attempts.")
        st.stop()

    final_spec = run.final_spec

else:
    from chart_llm.pipeline.generate import generate_spec  # noqa: E402

    with st.spinner(f"Generating with {model_name}…"):
        result = generate_spec(client, dataset_ctx, question)

    c1, c2, c3 = st.columns(3)
    c1.metric("Latency", f"{result.latency_ms:.0f} ms")
    c2.metric("Prompt tokens", result.prompt_tokens or "n/a")
    c3.metric("Completion tokens", result.completion_tokens or "n/a")

    final_spec = result.spec

# ── Render ────────────────────────────────────────────────────────────────────

from chart_llm.rendering import render_to_html  # noqa: E402

html = render_to_html(final_spec, dataset_ctx.df)
st.components.v1.html(html, height=500, scrolling=True)

with st.expander("Final Vega-Lite spec (JSON)", expanded=False):
    st.json(final_spec)

st.download_button(
    label="Download spec as JSON",
    data=json.dumps(final_spec, indent=2),
    file_name="chart_spec.json",
    mime="application/json",
)

html_download = render_to_html(final_spec, dataset_ctx.df)
st.download_button(
    label="Download chart as HTML",
    data=html_download,
    file_name="chart.html",
    mime="text/html",
)
