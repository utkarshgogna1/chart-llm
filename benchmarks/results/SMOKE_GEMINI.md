# Benchmark Report

## Summary

| Model | Mode | Queries | Succeeded | Errored |
| -------------------- | ------------ | ------- | ---------- | -------- |
| gemini-flash | baseline | 2 | 0 | 2 |
| gemini-flash | validated | 2 | 2 | 0 |

## Results

| Model | Mode | Validated | Correctness | No Hallucinations | Renders | Median Latency | Avg Attempts |
| -------------------- | ------------ | ---------- | ------------ | ------------------ | -------- | --------------- | ------------- |
| gemini-flash | baseline | 0% | 0% | 100% | 0% | 0 ms | 0.00 |
| gemini-flash | validated | 0% | 0% | 100% | 0% | 0 ms | 0.00 |

## Validation Impact

| Model | Validated Δ | Correctness Δ | No Hallucinations Δ | Renders Δ |
| -------------------- | ------------ | -------------- | -------------------- | ---------- |
| gemini-flash | 0% | 0% | 0% | 0% |

## Failure-Mode Taxonomy

| Category | Count |
| ------------------------- | ------ |
| generation_error | 2 |
| no_spec | 2 |

## Per-Query Details

### sales_001

| Model | Mode | Validated | Correct | Hallucinations | Renders | Latency |
| -------------------- | ------------ | ---------- | -------- | -------------- | -------- | ---------- |
| gemini-flash | baseline | ✗ | ✗ | none | ✗ | 0 ms |
| gemini-flash | validated | ✗ | ✗ | none | ✗ | 0 ms |

### sales_002

| Model | Mode | Validated | Correct | Hallucinations | Renders | Latency |
| -------------------- | ------------ | ---------- | -------- | -------------- | -------- | ---------- |
| gemini-flash | baseline | ✗ | ✗ | none | ✗ | 0 ms |
| gemini-flash | validated | ✗ | ✗ | none | ✗ | 0 ms |

## Reproducibility

- **Queries:** 2
- **Models:** gemini-flash
- **Vega-Lite schema:** Vega-Lite v5
- **Git SHA:** 0fc48f9
- **Total records:** 4
