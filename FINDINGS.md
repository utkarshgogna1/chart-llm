# Benchmark Findings

Reproducible benchmark over 5 hand-curated queries on the `sales.csv` dataset, two modes (baseline vs validated), three target models. n=5 is too small to claim statistical significance; these findings describe *behavior categories* observed, not population-level rates.

---

## Finding 1 — Llama-3-70B (Groq): the loop's only contribution is contract enforcement

Baseline produced semantically correct specs on 5/5 queries (Correctness 100%) but failed our internal contract on all of them — every spec used `"data": {"name": "sales"}` instead of the required `"name": "table"`. Validated mode forced the contract change and reached `final_validated` on 5/5. Average attempts: 1.00 in both modes; latency parity (486 ms validated vs 654 ms baseline median).

**Interpretation:** On a strong model with easy queries, the validation loop adds zero semantic correction. It's a quality gate enforcing system invariants. That's a real function in production (your downstream renderer assumes a specific data ref), but it shouldn't be confused with "the loop made the model smarter."

---

## Finding 2 — Llama-3.1-8B-local: validation can't compensate for model capability

Validation lifted spec validity from 0% to 60%, but semantic correctness stayed at 40% in both modes and render success dropped from 100% to 60% in validated mode. Investigation showed the failed renders were `no_spec` cases — the 8B model exhausted 3 attempts without producing any spec that cleared structural + data_ref validation.

**Interpretation:** The 8B model reinterprets retry feedback as license to rewrite the whole spec, rather than making targeted fixes. The validation loop's structured errors *don't help* a model that can't follow them precisely. With n=5 and a non-deterministic model, a single sample flip moves correctness by 20 points (sales_004 baseline correct in one run, validated wrong in the next, same prompt). Fixing this properly would require either constrained decoding, diff-style feedback (showing exact JSON paths that changed), or a higher-capacity model. None of those are cheap.

---

## Finding 3 — Gemini Flash: free-tier rate limits make benchmarking infeasible

10/10 records returned `Rate limited (429) on attempt 3` after the client's 5s/15s/45s backoff. Gemini's free tier (~15 RPM on `gemini-2.0-flash`) cannot sustain even a 5-query × 2-mode benchmark run without inter-query sleep. The harness's improved error reporting correctly distinguishes "API failure" from "model produced bad output," so the data is honest: we have no signal about Gemini's chart-generation capability from this run.

**Decision:** Gemini is excluded from the headline benchmark. Reproducing Gemini numbers would require either paid API access or harness-level rate-limit-aware scheduling (sleep N seconds between API-quota'd queries). Both are infrastructure work, not core to the project.

---

## Methodology notes

- **n=5** is *small*. These findings are directional, not statistical. Scaling to 20+ harder queries is planned and pending.
- The retry loop catches: schema mismatches, structural Vega-Lite mistakes, data-ref contract violations, hallucinated column names, semantic type mismatches, render failures. It cannot catch: wrong chart-type choices, wrong aggregations, missing channels the user implied but didn't state.
- Latency includes the validation loop overhead, which on the 70B free tier is approximately 1 extra LLM call when correction is needed (~500ms additional median).
