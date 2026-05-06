# chart-llm

**Natural-language → Vega-Lite chart generation with an LLM validation loop.**

Give it a CSV and a question in plain English. It asks an LLM to write a Vega-Lite spec, validates the spec against the official JSON schema *and* the data semantics of your CSV, and retries with targeted feedback if anything is wrong. The result is a rendered chart.

---

## How it works

```
CSV + Question
      │
      ▼
  LLM prompt
      │
      ▼
 Vega-Lite spec (JSON)
      │
      ├─► JSON schema validation  ─► errors?
      │                                  │ yes → retry with feedback (up to N times)
      └─► Semantic validation     ─► ────┘
              (field names, types)
      │ no errors
      ▼
  Render → HTML / PNG
```

Two modes per run:

| Mode | What it does |
|---|---|
| **baseline** | One LLM call, no validation, accept whatever comes back |
| **validated** | Schema + semantic checks, retry loop with structured error feedback |

---

## Benchmark: 3 models × 2 modes

The primary goal of this project is a reproducible public benchmark comparing:

| Model | Provider | Notes |
|---|---|---|
| **Gemini 2.0 Flash** | Google AI | Fast, multimodal, large context |
| **Llama-3-70B** | Groq | Open-weight, very fast inference via Groq API |
| **Llama-3.1-8B** | Ollama (local) | Fully offline, smallest model |

Each model is evaluated in both baseline and validated modes across a shared set of datasets and natural-language questions.

**Metrics collected:**
- First-pass validity rate (schema + semantics)
- Final validity rate after retry loop
- Average number of attempts needed
- Latency per chart (ms)
- *(Planned)* Human-rated visual correctness score

---

## Try it

> **Live demo:** *(deploy to Streamlit Community Cloud and paste URL here)*
>
> **Local demo:**
> ```bash
> streamlit run app.py
> ```

---

## Quickstart

```bash
# Install dependencies
uv sync

# Copy env file and add your keys
cp .env.example .env

# Download the Vega-Lite JSON schema (needed for validation)
chart-llm fetch-schema

# Generate a chart (baseline, no validation)
chart-llm generate data.csv "Show monthly sales as a bar chart" --model gemini-flash

# Generate with validation + retry loop
chart-llm generate data.csv "Show monthly sales as a bar chart" --model gemini-flash --validate

# Render a saved spec to HTML, PNG, or SVG
chart-llm render spec.json data.csv --out chart.html
chart-llm render spec.json data.csv --out chart.png

# Run the full benchmark
chart-llm benchmark
```

---

## Project layout

```
chart_llm/
  models/        # LLM adapters: Gemini, Groq, Ollama
  prompts/       # Prompt templates for generation and retry
  validation/    # JSON schema + data-semantic checks
  pipeline/      # Orchestration: generate → validate → retry
  rendering/     # Spec → HTML / PNG
  eval/          # Benchmark runner and metrics
  cli.py         # Typer CLI (chart-llm command)
tests/           # pytest suite
benchmarks/
  datasets/      # CSV files used in the benchmark
  queries/       # Natural-language questions per dataset
  results/       # Raw JSONL output from benchmark runs
```

---

## Status

- [x] Project structure and dependency setup
- [x] Abstract LLM model interface
- [x] Gemini 2.0 Flash adapter
- [x] Groq (Llama-3-70B) adapter
- [x] Ollama (Llama-3.1-8B) adapter
- [x] Prompt templates (generation + retry-with-feedback)
- [x] JSON schema validation (Vega-Lite v5)
- [x] Semantic validation (field names, types, aggregates)
- [x] Retry-with-feedback pipeline
- [x] HTML rendering (CDN-based, self-contained)
- [x] PNG / SVG rendering (vl-convert-python, pure-Rust)
- [x] CLI: `generate`, `render`, `validate`, `fetch-schema`, `test-model`
- [x] Streamlit web UI (`app.py`)
- [x] Benchmark datasets and queries
- [ ] Run benchmark, publish results

---

## Requirements

- Python 3.11+
- [uv](https://github.com/astral-sh/uv)
- API keys: `GEMINI_API_KEY`, `GROQ_API_KEY` (see `.env.example`)
- For PNG/SVG rendering: `vl-convert-python` (installed automatically, pure-Rust — no Node.js needed)
- For local Llama: [Ollama](https://ollama.com) running with `ollama pull llama3.1:8b`
