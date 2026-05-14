# Contributing

## Adding a new model

1. Create `chart_llm/models/<name>.py` implementing the `LLMModel` base class:

```python
from chart_llm.models.base import LLMModel, LLMResponse

class MyModelClient(LLMModel):
    def generate(self, system: str, user: str, max_retries: int = 2) -> LLMResponse:
        # call your API, return LLMResponse
        return LLMResponse(
            text="...",
            model_name="my-model",
            latency_ms=123.4,
            prompt_tokens=50,
            completion_tokens=100,
        )
```

2. Register it in `chart_llm/models/registry.py`:

```python
from chart_llm.models.my_model import MyModelClient

def get_client(name: str) -> LLMModel:
    ...
    if name == "my-model-name":
        return MyModelClient()
    ...
```

3. Add a smoke test: `uv run chart-llm test-model my-model-name`.

4. Run `uv run pytest tests/ -v` — all 192 tests should still pass (they mock the client).

---

## Adding a new benchmark query

Each query is a JSON file in `benchmarks/queries/<id>.json`. The schema:

```json
{
  "id": "dataset_NNN",
  "dataset": "dataset.csv",
  "question": "Plain-English question for the model.",
  "ground_truth_spec": {
    "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
    "data": { "name": "table" },
    "mark": "bar",
    "encoding": { ... }
  },
  "tags": ["bar", "aggregation"],
  "difficulty": "easy",
  "expects_no_correct_answer": false
}
```

**Requirements for the ground-truth spec:**
- `data.name` must be `"table"` — the pipeline injects data under this key.
- Must pass the full validation pipeline: `uv run pytest tests/test_eval.py::test_all_ground_truth_specs_pass_validation -v`.
- Use the canonical fieldless count form when the mark is a row count: `{"aggregate": "count", "type": "quantitative"}` (no `field` key).
- For queries with calculate-derived fields, include the `transform` step — the scorer matches on the `"as"` key only, not the expression text.

**For unanswerable queries** (the dataset lacks a column the question requires): set `expects_no_correct_answer: true` and omit `ground_truth_spec`. The benchmark records whether the model hallucinates a proxy chart (`no-answer-hallucinated`) or correctly produces nothing (`no-answer-honest`).

**After adding a query**, run:

```bash
uv run chart-llm bench list          # should show N+1 total
uv run pytest tests/test_eval.py -v  # test_load_benchmark_reads_23_queries will fail — update the count
```
