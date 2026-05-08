# Benchmark Report

## Summary

| Model | Mode | Queries | Succeeded | Errored |
| -------------------- | ------------ | ------- | ---------- | -------- |
| llama-8b-local | baseline | 5 | 5 | 0 |
| llama-8b-local | validated | 5 | 5 | 0 |

## Results

| Model | Mode | Validated | Correctness | No Hallucinations | Renders | Median Latency | Avg Attempts |
| -------------------- | ------------ | ---------- | ------------ | ------------------ | -------- | --------------- | ------------- |
| llama-8b-local | baseline | 0% | 40% | 100% | 100% | 5786 ms | 1.00 |
| llama-8b-local | validated | 60% | 40% | 100% | 60% | 10220 ms | 2.00 |

## Validation Impact

| Model | Validated Δ | Correctness Δ | No Hallucinations Δ | Renders Δ |
| -------------------- | ------------ | -------------- | -------------------- | ---------- |
| llama-8b-local | ↑60% | 0% | 0% | ↓40% |

## Failure-Mode Taxonomy

| Category | Count |
| ------------------------- | ------ |
| correct | 4 |
| wrong_aggregate | 3 |
| no_spec | 2 |
| wrong_encoding | 1 |

## Per-Query Details

### sales_001

| Model | Mode | Validated | Correct | Hallucinations | Renders | Latency |
| -------------------- | ------------ | ---------- | -------- | -------------- | -------- | ---------- |
| llama-8b-local | baseline | ✗ | ✓ | none | ✓ | 14302 ms |
| llama-8b-local | validated | ✓ | ✓ | none | ✓ | 4402 ms |

### sales_002

| Model | Mode | Validated | Correct | Hallucinations | Renders | Latency |
| -------------------- | ------------ | ---------- | -------- | -------------- | -------- | ---------- |
| llama-8b-local | baseline | ✗ | ✗ | none | ✓ | 5786 ms |
| llama-8b-local | validated | ✓ | ✓ | none | ✓ | 3941 ms |

### sales_003

| Model | Mode | Validated | Correct | Hallucinations | Renders | Latency |
| -------------------- | ------------ | ---------- | -------- | -------------- | -------- | ---------- |
| llama-8b-local | baseline | ✗ | ✗ | none | ✓ | 7077 ms |
| llama-8b-local | validated | ✗ | ✗ | none | ✗ | 22639 ms |

### sales_004

| Model | Mode | Validated | Correct | Hallucinations | Renders | Latency |
| -------------------- | ------------ | ---------- | -------- | -------------- | -------- | ---------- |
| llama-8b-local | baseline | ✗ | ✓ | none | ✓ | 5044 ms |
| llama-8b-local | validated | ✗ | ✗ | none | ✗ | 19240 ms |

### sales_005

| Model | Mode | Validated | Correct | Hallucinations | Renders | Latency |
| -------------------- | ------------ | ---------- | -------- | -------------- | -------- | ---------- |
| llama-8b-local | baseline | ✗ | ✗ | none | ✓ | 5338 ms |
| llama-8b-local | validated | ✓ | ✗ | none | ✓ | 10220 ms |

## Reproducibility

- **Queries:** 5
- **Models:** llama-8b-local
- **Vega-Lite schema:** Vega-Lite v5
- **Git SHA:** 0fc48f9
- **Total records:** 10
