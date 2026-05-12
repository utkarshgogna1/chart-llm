# Benchmark Report

## Summary

| Model | Mode | Queries | Succeeded | Errored | No Spec |
| -------------------- | ------------ | ------- | ---------- | -------- | -------- |
| llama-70b-groq | baseline | 5 | 0 | 0 | 5 |
| llama-70b-groq | validated | 5 | 5 | 0 | 0 |

## Results

| Model | Mode | Validated | Correctness | No Hallucinations | Renders | Median Latency | Avg Attempts |
| -------------------- | ------------ | ---------- | ------------ | ------------------ | -------- | --------------- | ------------- |
| llama-70b-groq | baseline | 0% | 100% | 100% | 100% | 654 ms | 1.00 |
| llama-70b-groq | validated | 100% | 100% | 100% | 100% | 486 ms | 1.00 |

## Validation Impact

| Model | Validated Δ | Correctness Δ | No Hallucinations Δ | Renders Δ |
| -------------------- | ------------ | -------------- | -------------------- | ---------- |
| llama-70b-groq | ↑100% | 0% | 0% | 0% |

## Failure-Mode Taxonomy

| Category | Count |
| ------------------------- | ------ |
| correct | 10 |

## Per-Query Details

### sales_001

| Model | Mode | Validated | Correct | Hallucinations | Renders | Latency |
| -------------------- | ------------ | ---------- | -------- | -------------- | -------- | ---------- |
| llama-70b-groq | baseline | ✗ | ✓ | none | ✓ | 654 ms |
| llama-70b-groq | validated | ✓ | ✓ | none | ✓ | 421 ms |

### sales_002

| Model | Mode | Validated | Correct | Hallucinations | Renders | Latency |
| -------------------- | ------------ | ---------- | -------- | -------------- | -------- | ---------- |
| llama-70b-groq | baseline | ✗ | ✓ | none | ✓ | 654 ms |
| llama-70b-groq | validated | ✓ | ✓ | none | ✓ | 485 ms |

### sales_003

| Model | Mode | Validated | Correct | Hallucinations | Renders | Latency |
| -------------------- | ------------ | ---------- | -------- | -------------- | -------- | ---------- |
| llama-70b-groq | baseline | ✗ | ✓ | none | ✓ | 520 ms |
| llama-70b-groq | validated | ✓ | ✓ | none | ✓ | 486 ms |

### sales_004

| Model | Mode | Validated | Correct | Hallucinations | Renders | Latency |
| -------------------- | ------------ | ---------- | -------- | -------------- | -------- | ---------- |
| llama-70b-groq | baseline | ✗ | ✓ | none | ✓ | 861 ms |
| llama-70b-groq | validated | ✓ | ✓ | none | ✓ | 533 ms |

### sales_005

| Model | Mode | Validated | Correct | Hallucinations | Renders | Latency |
| -------------------- | ------------ | ---------- | -------- | -------------- | -------- | ---------- |
| llama-70b-groq | baseline | ✗ | ✓ | none | ✓ | 425 ms |
| llama-70b-groq | validated | ✓ | ✓ | none | ✓ | 721 ms |

## Reproducibility

- **Queries:** 5
- **Models:** llama-70b-groq
- **Vega-Lite schema:** Vega-Lite v5
- **Git SHA:** 4b6d7ef
- **Total records:** 10
