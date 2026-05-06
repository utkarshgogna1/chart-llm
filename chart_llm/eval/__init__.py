"""Evaluation harness for the 3-model benchmark."""

from chart_llm.eval.queries import BenchmarkQuery, load_benchmark
from chart_llm.eval.report import build_report
from chart_llm.eval.runner import BenchmarkRecord, run_benchmark
from chart_llm.eval.scoring import CorrectnessScore, RenderCheck, hallucinated_columns, render_check, spec_correctness

__all__ = [
    "BenchmarkQuery",
    "BenchmarkRecord",
    "CorrectnessScore",
    "RenderCheck",
    "build_report",
    "hallucinated_columns",
    "load_benchmark",
    "render_check",
    "run_benchmark",
    "spec_correctness",
]
