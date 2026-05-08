# Benchmark Findings

## Llama-3.1-8B-local on the 5-query smoke benchmark

**Headline:** Validation loop improves spec validity from 0% to 60% but does not improve semantic correctness (40% in both modes), and exposes a real architectural limitation in how 8B models respond to feedback.

**Analysis (after render-as-validator fix and tighter retry prompt):**

The render validation stage and the tighter retry prompt are structurally correct additions, but they don't address the 8B model's actual failure mode. Both "renders=False" entries in the report are `no_spec` cases — the model never produced a spec that cleared structural + data_ref validation in 3 attempts. The render check would only fire after all previous stages pass; that threshold is never reached for these queries. The tighter prompt ("make the smallest change") had mixed effects: sales_005 now passes in 2 attempts (previously failing), but sales_004 validated regressed from 1-attempt success to max_attempts failure — almost certainly stochastic variance, since baseline got sales_004 exactly right with an identical first-attempt prompt. With n=5 queries and a non-deterministic model, a single LLM call swapping good-to-bad inverts a 20-point metric. The real remaining gap is architectural: the 8B model reinterprets validation feedback as license to rewrite the whole spec rather than making targeted fixes. Fixing this properly requires either constrained decoding, diff-style feedback (show exactly which JSON paths changed), or a higher-capacity model.
