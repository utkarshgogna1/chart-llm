# Benchmark Findings

Reproducible benchmark over 23 hand-curated queries across 3 datasets (sales, movies, weather), two modes per model (baseline vs validated with retry loop), two target models. Gemini Flash excluded — free-tier rate-limited; documented separately. n=23 is still small; these findings describe behavior categories observed in this run, not population-level rates.

---

## Headline numbers

| Model | Mode | Spec validity | Correctness | No hallucinations | Renders | Median latency | Avg attempts |
|---|---|---|---|---|---|---|---|
| Llama-3-70B (Groq) | baseline | 0% | 77% | 100% | 100% | 568 ms | 1.00 |
| Llama-3-70B (Groq) | validated | 78% | 68% | 100% | 78% | 589 ms | 1.52 |
| Llama-3.1-8B (Ollama) | baseline | 0% | 27% | 83% | 91% | 6213 ms | 0.91 |
| Llama-3.1-8B (Ollama) | validated | 39% | 23% | 100% | 39% | 16396 ms | 2.26 |

---

## Finding 1 — Validation loop is "contract enforcement," not "model improvement"

On the 70B, the validation loop's primary contribution is forcing the generated spec to satisfy our internal contract (`data.name=table`, no facet-in-encoding, no top-level filters, valid Vega-Lite v5 schema). Spec validity rises from 0% to 78% at essentially zero latency cost (568→589 ms median, 1.52 avg attempts). This is real value in production — your downstream renderer assumes a specific data ref, and the loop guarantees it — but it's not the same as making the model semantically smarter.

Correctness on the 70B *fell* from 77% to 68% in validated mode. The drop is partly an artifact of the new (stricter) scorer correctly catching a previously false-positive faceted spec on sales_006, and partly real: on movies_004, the retry feedback caused the model to drop its window/rank transform and produce a degraded spec. The loop is not free.

## Finding 2 — Validation cannot substitute for model capability

On the 8B, validation lifted spec validity from 0% to 39%, but correctness stayed flat (27% → 23%) and render success collapsed from 91% to 39%. The retry loop spent its budget producing specs that failed every attempt; average attempts climbed to 2.26 with most queries hitting max-attempts without a valid spec. Latency rose 2.6× to 16.4 seconds per query.

The hallucination prevention metric (+17 points, 83%→100%) is the one genuine win for the 8B — the validator does catch real column inventions even at small model size.

The structural verdict: at 16 seconds per query for 39% validity and lower correctness than baseline, the validation loop on the 8B doesn't pay for itself. The 8B reinterprets retry feedback as license to rewrite the whole spec rather than make targeted fixes. Fixing this properly would require constrained decoding, diff-style feedback (showing exact JSON paths that changed), or a higher-capacity model.

## Finding 3 — True capability gaps are query-shaped, not model-shaped

Four queries failed in both modes for both models: movies_008 (calculate-derived highlight field), sales_007 (calculate-derived quarter label), weather_005 (top-N aggregation across cities), weather_006 (calculate-derived rainy-day rate). Common pattern: each requires either a calculate transform with a non-trivial expression, or a window/rank transform. Neither model generates these reliably in a form the validators accept. These represent genuine skill gaps, not bad luck or scoring artifacts.

## Finding 4 — The "no-answer" probe paid off

movies_007 ("show me directors by box office" — the dataset has no `director` column) was designed as an unanswerable question. In baseline, the 70B invented a derived `total_box_office` proxy (recorded as no-answer-hallucinated) and the 8B used `studio` as a stand-in. Both were stopped by the validation loop in validated mode (no-answer-honest). The loop's clearest single-query win in the benchmark.

## Finding 5 — Scorer correctness is itself an artifact worth validating

During this project, three separate scoring bugs were caught and fixed *after* preliminary results were generated:

1. **Faceted-spec detection.** The original `_extract_mark` returned empty string for faceted specs; sales_006 was scored as a false-positive match.
2. **Count-form equivalence.** Fielded vs fieldless count specs needed to score as equivalent.
3. **Derived-field hallucination false-positives.** The hallucination scorer didn't share the column validator's derived-field detection; values like `temp_range` (from a `calculate`) were flagged as hallucinated columns.

Each fix moved real numbers. The pre-fix 70B "no-hallucinations Δ" was reported as +22%; the corrected number is 0% (baseline was already 100% once derived fields are properly excluded). Lesson: an LLM benchmark is only as honest as its scorer, and scorer bugs masquerade as model wins. Worth saying out loud.

---

## Methodology notes

- **n=23** is directional, not statistical.
- **Gemini Flash** was excluded after 10/10 records returned `Rate limited (429)` even with 5s/15s/45s backoff. Free-tier quota (~15 RPM) cannot sustain a 23-query × 2-mode run.
- Validation stages currently catch: schema mismatches, structural Vega-Lite mistakes (facet/row/column nested in encoding, filter at top level), data-ref contract violations, hallucinated column names (with derived-field exclusion), semantic type mismatches, render failures.
- Validation cannot catch: wrong chart-type choices, wrong aggregations, missing channels the user implied but didn't state, charts that render but answer the wrong question.
- 192 unit tests cover models, validation, retry, rendering, scoring, datasets.
