# Benchmark Report

## Summary

| Model | Mode | Queries | Succeeded | Errored |
| -------------------- | ------------ | ------- | ---------- | -------- |
| llama-70b-groq | baseline | 5 | 5 | 0 |
| llama-70b-groq | validated | 5 | 5 | 0 |

## Results

| Model | Mode | Validated | Correctness | No Hallucinations | Renders | Median Latency | Avg Attempts |
| -------------------- | ------------ | ---------- | ------------ | ------------------ | -------- | --------------- | ------------- |
| llama-70b-groq | baseline | 0% | 100% | 100% | 100% | 487 ms | 1.00 |
| llama-70b-groq | validated | 100% | 100% | 100% | 100% | 601 ms | 1.20 |

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
| llama-70b-groq | baseline | ✗ | ✓ | none | ✓ | 593 ms |
| llama-70b-groq | validated | ✓ | ✓ | none | ✓ | 449 ms |

### sales_002

| Model | Mode | Validated | Correct | Hallucinations | Renders | Latency |
| -------------------- | ------------ | ---------- | -------- | -------------- | -------- | ---------- |
| llama-70b-groq | baseline | ✗ | ✓ | none | ✓ | 389 ms |
| llama-70b-groq | validated | ✓ | ✓ | none | ✓ | 611 ms |

### sales_003

| Model | Mode | Validated | Correct | Hallucinations | Renders | Latency |
| -------------------- | ------------ | ---------- | -------- | -------------- | -------- | ---------- |
| llama-70b-groq | baseline | ✗ | ✓ | none | ✓ | 487 ms |
| llama-70b-groq | validated | ✓ | ✓ | none | ✓ | 601 ms |

### sales_004

| Model | Mode | Validated | Correct | Hallucinations | Renders | Latency |
| -------------------- | ------------ | ---------- | -------- | -------------- | -------- | ---------- |
| llama-70b-groq | baseline | ✗ | ✓ | none | ✓ | 475 ms |
| llama-70b-groq | validated | ✓ | ✓ | none | ✓ | 996 ms |

### sales_005

| Model | Mode | Validated | Correct | Hallucinations | Renders | Latency |
| -------------------- | ------------ | ---------- | -------- | -------------- | -------- | ---------- |
| llama-70b-groq | baseline | ✗ | ✓ | none | ✓ | 488 ms |
| llama-70b-groq | validated | ✓ | ✓ | none | ✓ | 517 ms |

## Reproducibility

- **Queries:** 5
- **Models:** llama-70b-groq
- **Vega-Lite schema:** Vega-Lite v5
- **Git SHA:** eabdc15
- **Total records:** 10
