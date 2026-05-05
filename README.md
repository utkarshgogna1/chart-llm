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

## Quickstart

```bash
# Install dependencies
uv sync

# Copy env file and add your keys
cp .env.example .env

# Download the Vega-Lite JSON schema (needed for validation)
chart-llm fetch-schema

# Generate a chart
chart-llm generate data.csv "Show monthly sales as a bar chart" --model gemini

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

## Status: scaffolding

- [x] Project structure and dependency setup
- [x] Abstract LLM model interface
- [x] Model adapter stubs (Gemini, Groq, Ollama)
- [x] Prompt templates (generation + retry-with-feedback)
- [x] Validation stubs (schema, semantic)
- [x] Pipeline and retry loop stubs
- [x] Rendering stubs (HTML, PNG)
- [x] Eval runner and metrics stubs
- [x] CLI commands (generate, benchmark, fetch-schema)
- [ ] Implement Gemini adapter
- [ ] Implement Groq adapter
- [ ] Implement Ollama adapter
- [ ] Implement schema validation (download vega-lite-schema.json)
- [ ] Implement semantic validation
- [ ] Implement retry pipeline
- [ ] Implement HTML rendering
- [ ] Add benchmark datasets and queries
- [ ] Run benchmark, publish results

---

## Requirements

- Python 3.11+
- [uv](https://github.com/astral-sh/uv)
- API keys: `GEMINI_API_KEY`, `GROQ_API_KEY` (see `.env.example`)
- For PNG rendering: Node.js + `npm i -g vega-cli`
- For local Llama: [Ollama](https://ollama.com) running with `ollama pull llama3.1:8b`
