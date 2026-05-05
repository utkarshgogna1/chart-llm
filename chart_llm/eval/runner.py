"""Benchmark runner: iterate over datasets × queries × models, collect metrics."""

import asyncio
import json
from pathlib import Path

import pandas as pd

from chart_llm.eval.metrics import SpecMetrics, aggregate
from chart_llm.models.base import LLMModel
from chart_llm.pipeline import run_pipeline

# TODO: load queries from benchmarks/queries/*.json
# TODO: load datasets from benchmarks/datasets/*.csv
# TODO: write per-run results to benchmarks/results/{run_id}.jsonl


async def run_benchmark(
    models: list[LLMModel],
    datasets_dir: Path,
    queries_dir: Path,
    results_dir: Path,
    max_retries: int = 3,
    validate: bool = True,
) -> dict:
    """Run the full benchmark and return aggregated metrics by model."""
    all_metrics: list[SpecMetrics] = []

    # TODO: iterate datasets, load CSV, iterate matching queries, iterate models
    # TODO: call run_pipeline for each combination, capture SpecMetrics
    # TODO: write raw results to JSONL incrementally (so partial runs are recoverable)

    return aggregate(all_metrics)


def run_benchmark_sync(*args, **kwargs) -> dict:
    return asyncio.run(run_benchmark(*args, **kwargs))
