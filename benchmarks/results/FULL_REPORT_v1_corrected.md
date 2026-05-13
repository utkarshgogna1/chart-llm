# Benchmark Report

## Summary

| Model | Mode | Queries | Succeeded | Errored | No Spec |
| -------------------- | ------------ | ------- | ---------- | -------- | -------- |
| llama-70b-groq | baseline | 23 | 0 | 0 | 23 |
| llama-70b-groq | validated | 23 | 18 | 0 | 5 |
| llama-8b-local | baseline | 23 | 0 | 2 | 21 |
| llama-8b-local | validated | 23 | 9 | 0 | 14 |

## Results

| Model | Mode | Validated | Correctness | No Hallucinations | Renders | Median Latency | Avg Attempts |
| -------------------- | ------------ | ---------- | ------------ | ------------------ | -------- | --------------- | ------------- |
| llama-70b-groq | baseline | 0% | 77% | 100% | 100% | 568 ms | 1.00 |
| llama-70b-groq | validated | 78% | 68% | 100% | 78% | 589 ms | 1.52 |
| llama-8b-local | baseline | 0% | 27% | 83% | 91% | 6213 ms | 0.91 |
| llama-8b-local | validated | 39% | 23% | 100% | 39% | 16396 ms | 2.26 |

## Validation Impact

| Model | Validated Δ | Correctness Δ | No Hallucinations Δ | Renders Δ |
| -------------------- | ------------ | -------------- | -------------------- | ---------- |
| llama-70b-groq | ↑78% | ↓9% | 0% | ↓22% |
| llama-8b-local | ↑39% | ↓5% | ↑17% | ↓52% |

## Failure-Mode Taxonomy

| Category | Count |
| ------------------------- | ------ |
| correct | 43 |
| no_spec | 17 |
| wrong_encoding | 14 |
| wrong_aggregate | 9 |
| wrong_mark | 3 |
| generation_error | 2 |
| no-answer-hallucinated | 2 |
| no-answer-honest | 2 |

## Per-Query Details

### movies_001

| Model | Mode | Validated | Correct | Hallucinations | Renders | Latency |
| -------------------- | ------------ | ---------- | -------- | -------------- | -------- | ---------- |
| llama-70b-groq | baseline | ✗ | ✓ | none | ✓ | 734 ms |
| llama-70b-groq | validated | ✓ | ✓ | none | ✓ | 457 ms |
| llama-8b-local | baseline | ✗ | ✗ | none | ✗ | 0 ms |
| llama-8b-local | validated | ✗ | ✗ | none | ✗ | 18210 ms |

### movies_002

| Model | Mode | Validated | Correct | Hallucinations | Renders | Latency |
| -------------------- | ------------ | ---------- | -------- | -------------- | -------- | ---------- |
| llama-70b-groq | baseline | ✗ | ✓ | none | ✓ | 585 ms |
| llama-70b-groq | validated | ✓ | ✓ | none | ✓ | 486 ms |
| llama-8b-local | baseline | ✗ | ✓ | none | ✓ | 6005 ms |
| llama-8b-local | validated | ✓ | ✓ | none | ✓ | 10173 ms |

### movies_003

| Model | Mode | Validated | Correct | Hallucinations | Renders | Latency |
| -------------------- | ------------ | ---------- | -------- | -------------- | -------- | ---------- |
| llama-70b-groq | baseline | ✗ | ✓ | none | ✓ | 510 ms |
| llama-70b-groq | validated | ✓ | ✓ | none | ✓ | 589 ms |
| llama-8b-local | baseline | ✗ | ✓ | none | ✓ | 5134 ms |
| llama-8b-local | validated | ✓ | ✓ | none | ✓ | 4080 ms |

### movies_004

| Model | Mode | Validated | Correct | Hallucinations | Renders | Latency |
| -------------------- | ------------ | ---------- | -------- | -------------- | -------- | ---------- |
| llama-70b-groq | baseline | ✗ | ✓ | none | ✓ | 429 ms |
| llama-70b-groq | validated | ✗ | ✗ | none | ✗ | 2212 ms |
| llama-8b-local | baseline | ✗ | ✗ | ['sum(box_office_usd)'] | ✓ | 7712 ms |
| llama-8b-local | validated | ✗ | ✗ | none | ✗ | 25530 ms |

### movies_005

| Model | Mode | Validated | Correct | Hallucinations | Renders | Latency |
| -------------------- | ------------ | ---------- | -------- | -------------- | -------- | ---------- |
| llama-70b-groq | baseline | ✗ | ✓ | none | ✓ | 551 ms |
| llama-70b-groq | validated | ✓ | ✓ | none | ✓ | 508 ms |
| llama-8b-local | baseline | ✗ | ✓ | none | ✓ | 6474 ms |
| llama-8b-local | validated | ✗ | ✗ | none | ✗ | 24849 ms |

### movies_006

| Model | Mode | Validated | Correct | Hallucinations | Renders | Latency |
| -------------------- | ------------ | ---------- | -------- | -------------- | -------- | ---------- |
| llama-70b-groq | baseline | ✗ | ✓ | none | ✓ | 471 ms |
| llama-70b-groq | validated | ✓ | ✓ | none | ✓ | 464 ms |
| llama-8b-local | baseline | ✗ | ✓ | none | ✓ | 8500 ms |
| llama-8b-local | validated | ✗ | ✗ | none | ✗ | 21940 ms |

### movies_007

| Model | Mode | Validated | Correct | Hallucinations | Renders | Latency |
| -------------------- | ------------ | ---------- | -------- | -------------- | -------- | ---------- |
| llama-70b-groq | baseline | ✗ | — | none | ✓ | 588 ms |
| llama-70b-groq | validated | ✗ | — | none | ✗ | 1371 ms |
| llama-8b-local | baseline | ✗ | — | none | ✓ | 5298 ms |
| llama-8b-local | validated | ✗ | — | none | ✗ | 26522 ms |

### movies_008

| Model | Mode | Validated | Correct | Hallucinations | Renders | Latency |
| -------------------- | ------------ | ---------- | -------- | -------------- | -------- | ---------- |
| llama-70b-groq | baseline | ✗ | ✗ | none | ✓ | 679 ms |
| llama-70b-groq | validated | ✓ | ✗ | none | ✓ | 1591 ms |
| llama-8b-local | baseline | ✗ | ✗ | none | ✓ | 7551 ms |
| llama-8b-local | validated | ✓ | ✗ | none | ✓ | 6546 ms |

### sales_001

| Model | Mode | Validated | Correct | Hallucinations | Renders | Latency |
| -------------------- | ------------ | ---------- | -------- | -------------- | -------- | ---------- |
| llama-70b-groq | baseline | ✗ | ✓ | none | ✓ | 440 ms |
| llama-70b-groq | validated | ✓ | ✓ | none | ✓ | 403 ms |
| llama-8b-local | baseline | ✗ | ✗ | ['sum(revenue)'] | ✓ | 5268 ms |
| llama-8b-local | validated | ✗ | ✗ | none | ✗ | 16380 ms |

### sales_002

| Model | Mode | Validated | Correct | Hallucinations | Renders | Latency |
| -------------------- | ------------ | ---------- | -------- | -------------- | -------- | ---------- |
| llama-70b-groq | baseline | ✗ | ✓ | none | ✓ | 381 ms |
| llama-70b-groq | validated | ✓ | ✓ | none | ✓ | 593 ms |
| llama-8b-local | baseline | ✗ | ✗ | none | ✓ | 5133 ms |
| llama-8b-local | validated | ✓ | ✗ | none | ✓ | 4272 ms |

### sales_003

| Model | Mode | Validated | Correct | Hallucinations | Renders | Latency |
| -------------------- | ------------ | ---------- | -------- | -------------- | -------- | ---------- |
| llama-70b-groq | baseline | ✗ | ✓ | none | ✓ | 570 ms |
| llama-70b-groq | validated | ✓ | ✓ | none | ✓ | 476 ms |
| llama-8b-local | baseline | ✗ | ✗ | none | ✓ | 6172 ms |
| llama-8b-local | validated | ✗ | ✗ | none | ✗ | 19783 ms |

### sales_004

| Model | Mode | Validated | Correct | Hallucinations | Renders | Latency |
| -------------------- | ------------ | ---------- | -------- | -------------- | -------- | ---------- |
| llama-70b-groq | baseline | ✗ | ✓ | none | ✓ | 547 ms |
| llama-70b-groq | validated | ✓ | ✓ | none | ✓ | 541 ms |
| llama-8b-local | baseline | ✗ | ✗ | ['sum(units)'] | ✓ | 6213 ms |
| llama-8b-local | validated | ✓ | ✗ | none | ✓ | 4711 ms |

### sales_005

| Model | Mode | Validated | Correct | Hallucinations | Renders | Latency |
| -------------------- | ------------ | ---------- | -------- | -------------- | -------- | ---------- |
| llama-70b-groq | baseline | ✗ | ✓ | none | ✓ | 540 ms |
| llama-70b-groq | validated | ✓ | ✓ | none | ✓ | 624 ms |
| llama-8b-local | baseline | ✗ | ✗ | none | ✓ | 4386 ms |
| llama-8b-local | validated | ✗ | ✗ | none | ✗ | 15994 ms |

### sales_006

| Model | Mode | Validated | Correct | Hallucinations | Renders | Latency |
| -------------------- | ------------ | ---------- | -------- | -------------- | -------- | ---------- |
| llama-70b-groq | baseline | ✗ | ✓ | none | ✓ | 572 ms |
| llama-70b-groq | validated | ✓ | ✗ | none | ✓ | 545 ms |
| llama-8b-local | baseline | ✗ | ✗ | none | ✓ | 6050 ms |
| llama-8b-local | validated | ✗ | ✗ | none | ✗ | 16396 ms |

### sales_007

| Model | Mode | Validated | Correct | Hallucinations | Renders | Latency |
| -------------------- | ------------ | ---------- | -------- | -------------- | -------- | ---------- |
| llama-70b-groq | baseline | ✗ | ✗ | none | ✓ | 853 ms |
| llama-70b-groq | validated | ✓ | ✗ | none | ✓ | 591 ms |
| llama-8b-local | baseline | ✗ | ✗ | none | ✓ | 7947 ms |
| llama-8b-local | validated | ✓ | ✗ | none | ✓ | 6319 ms |

### weather_001

| Model | Mode | Validated | Correct | Hallucinations | Renders | Latency |
| -------------------- | ------------ | ---------- | -------- | -------------- | -------- | ---------- |
| llama-70b-groq | baseline | ✗ | ✓ | none | ✓ | 680 ms |
| llama-70b-groq | validated | ✓ | ✓ | none | ✓ | 433 ms |
| llama-8b-local | baseline | ✗ | ✓ | none | ✓ | 5105 ms |
| llama-8b-local | validated | ✗ | ✗ | none | ✗ | 22641 ms |

### weather_002

| Model | Mode | Validated | Correct | Hallucinations | Renders | Latency |
| -------------------- | ------------ | ---------- | -------- | -------------- | -------- | ---------- |
| llama-70b-groq | baseline | ✗ | ✓ | none | ✓ | 477 ms |
| llama-70b-groq | validated | ✓ | ✓ | none | ✓ | 450 ms |
| llama-8b-local | baseline | ✗ | ✗ | none | ✓ | 8403 ms |
| llama-8b-local | validated | ✗ | ✗ | none | ✗ | 30477 ms |

### weather_003

| Model | Mode | Validated | Correct | Hallucinations | Renders | Latency |
| -------------------- | ------------ | ---------- | -------- | -------------- | -------- | ---------- |
| llama-70b-groq | baseline | ✗ | ✓ | none | ✓ | 478 ms |
| llama-70b-groq | validated | ✓ | ✓ | none | ✓ | 1011 ms |
| llama-8b-local | baseline | ✗ | ✗ | ['average_precipitation_in'] | ✓ | 7870 ms |
| llama-8b-local | validated | ✓ | ✓ | none | ✓ | 6197 ms |

### weather_004

| Model | Mode | Validated | Correct | Hallucinations | Renders | Latency |
| -------------------- | ------------ | ---------- | -------- | -------------- | -------- | ---------- |
| llama-70b-groq | baseline | ✗ | ✓ | none | ✓ | 568 ms |
| llama-70b-groq | validated | ✓ | ✓ | none | ✓ | 598 ms |
| llama-8b-local | baseline | ✗ | ✗ | none | ✗ | 0 ms |
| llama-8b-local | validated | ✓ | ✓ | none | ✓ | 6678 ms |

### weather_005

| Model | Mode | Validated | Correct | Hallucinations | Renders | Latency |
| -------------------- | ------------ | ---------- | -------- | -------------- | -------- | ---------- |
| llama-70b-groq | baseline | ✗ | ✗ | none | ✓ | 785 ms |
| llama-70b-groq | validated | ✗ | ✗ | none | ✗ | 1586 ms |
| llama-8b-local | baseline | ✗ | ✗ | none | ✓ | 9469 ms |
| llama-8b-local | validated | ✗ | ✗ | none | ✗ | 26254 ms |

### weather_006

| Model | Mode | Validated | Correct | Hallucinations | Renders | Latency |
| -------------------- | ------------ | ---------- | -------- | -------------- | -------- | ---------- |
| llama-70b-groq | baseline | ✗ | ✗ | none | ✓ | 796 ms |
| llama-70b-groq | validated | ✗ | ✗ | none | ✗ | 1533 ms |
| llama-8b-local | baseline | ✗ | ✗ | none | ✓ | 8628 ms |
| llama-8b-local | validated | ✗ | ✗ | none | ✗ | 34956 ms |

### weather_007

| Model | Mode | Validated | Correct | Hallucinations | Renders | Latency |
| -------------------- | ------------ | ---------- | -------- | -------------- | -------- | ---------- |
| llama-70b-groq | baseline | ✗ | ✗ | none | ✓ | 790 ms |
| llama-70b-groq | validated | ✗ | ✗ | none | ✗ | 2071 ms |
| llama-8b-local | baseline | ✗ | ✗ | none | ✓ | 7993 ms |
| llama-8b-local | validated | ✓ | ✓ | none | ✓ | 6641 ms |

### weather_008

| Model | Mode | Validated | Correct | Hallucinations | Renders | Latency |
| -------------------- | ------------ | ---------- | -------- | -------------- | -------- | ---------- |
| llama-70b-groq | baseline | ✗ | ✓ | none | ✓ | 442 ms |
| llama-70b-groq | validated | ✓ | ✓ | none | ✓ | 397 ms |
| llama-8b-local | baseline | ✗ | ✓ | none | ✓ | 6940 ms |
| llama-8b-local | validated | ✗ | ✗ | none | ✗ | 25134 ms |

## Reproducibility

- **Queries:** 23
- **Models:** llama-70b-groq, llama-8b-local
- **Vega-Lite schema:** Vega-Lite v5
- **Git SHA:** d42ddb7
- **Total records:** 92
