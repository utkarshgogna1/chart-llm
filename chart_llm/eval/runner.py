"""Benchmark runner: iterate queries × models × modes, record results to JSONL."""

import json
import time
from pathlib import Path
from typing import Literal, Optional

import httpx
from pydantic import BaseModel
from rich.progress import BarColumn, MofNCompleteColumn, Progress, SpinnerColumn, TextColumn

from chart_llm.eval.queries import BenchmarkQuery, load_benchmark
from chart_llm.eval.scoring import (
    CorrectnessScore,
    RenderCheck,
    hallucinated_columns as _check_hallucinated,
    render_check as _check_render,
    spec_correctness,
)
from chart_llm.models.registry import get_client
from chart_llm.pipeline.dataset import build_dataset_context
from chart_llm.pipeline.generate import generate_spec
from chart_llm.pipeline.retry import generate_validated_spec


class BenchmarkRecord(BaseModel):
    query_id: str
    model: str
    mode: Literal["baseline", "validated"]
    attempts: int
    final_validated: bool
    final_spec: Optional[dict]
    correctness: CorrectnessScore
    hallucinated_columns: list[str]
    render_check: RenderCheck
    latency_ms: float
    prompt_tokens: Optional[int]
    completion_tokens: Optional[int]
    stop_reason: Optional[str]
    error_message: Optional[str]


def _error_record(
    query_id: str,
    model: str,
    mode: Literal["baseline", "validated"],
    error_message: str,
) -> BenchmarkRecord:
    return BenchmarkRecord(
        query_id=query_id,
        model=model,
        mode=mode,
        attempts=0,
        final_validated=False,
        final_spec=None,
        correctness=CorrectnessScore(match=False, mismatches=[]),
        hallucinated_columns=[],
        render_check=RenderCheck(ok=False),
        latency_ms=0.0,
        prompt_tokens=None,
        completion_tokens=None,
        stop_reason=None,
        error_message=error_message,
    )


def _load_done_keys(output_path: Path) -> set[tuple[str, str, str]]:
    done: set[tuple[str, str, str]] = set()
    if not output_path.exists():
        return done
    for line in output_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
            done.add((rec["query_id"], rec["model"], rec["mode"]))
        except (json.JSONDecodeError, KeyError):
            pass
    return done


def _run_single(
    query: BenchmarkQuery,
    model_name: str,
    mode: Literal["baseline", "validated"],
    datasets_dir: Path,
    max_attempts: int,
) -> BenchmarkRecord:
    dataset_ctx = build_dataset_context(datasets_dir / query.dataset)
    client = get_client(model_name)

    if mode == "baseline":
        result = generate_spec(client, dataset_ctx, query.question)
        final_spec: Optional[dict] = result.spec
        attempts = 1
        final_validated = False
        latency_ms = result.latency_ms
        prompt_tokens = result.prompt_tokens
        completion_tokens = result.completion_tokens
        stop_reason = "baseline"
    else:
        run = generate_validated_spec(client, dataset_ctx, query.question, max_attempts=max_attempts)
        final_spec = run.final_spec
        attempts = len(run.attempts)
        final_validated = run.succeeded
        latency_ms = run.total_latency_ms
        tok = run.total_tokens
        prompt_tokens = tok.prompt or None
        completion_tokens = tok.completion or None
        stop_reason = run.stop_reason

    if final_spec is not None:
        correctness = spec_correctness(final_spec, query.ground_truth_spec)
        hall = _check_hallucinated(final_spec, dataset_ctx)
        rc = _check_render(final_spec, dataset_ctx.df)
    else:
        correctness = CorrectnessScore(match=False, mismatches=["no spec generated"])
        hall = []
        rc = RenderCheck(ok=False, error="no spec generated")

    return BenchmarkRecord(
        query_id=query.id,
        model=model_name,
        mode=mode,
        attempts=attempts,
        final_validated=final_validated,
        final_spec=final_spec,
        correctness=correctness,
        hallucinated_columns=hall,
        render_check=rc,
        latency_ms=latency_ms,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        stop_reason=stop_reason,
        error_message=None,
    )


def run_benchmark(
    model_names: list[str],
    modes: list[Literal["baseline", "validated"]],
    queries_dir: Path,
    datasets_dir: Path,
    output_path: Path,
    max_attempts: int = 3,
    resume: bool = True,
) -> None:
    """Run all (query, model, mode) triples, appending BenchmarkRecord lines to output_path."""
    queries = load_benchmark(queries_dir)
    done = _load_done_keys(output_path) if resume else set()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    triples = [
        (q, m, mo)
        for q in queries
        for m in model_names
        for mo in modes
        if (q.id, m, mo) not in done
    ]

    with output_path.open("a", encoding="utf-8") as out_f:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            MofNCompleteColumn(),
            transient=True,
        ) as progress:
            task = progress.add_task("Running benchmark…", total=len(triples))
            for query, model_name, mode in triples:
                progress.update(
                    task,
                    description=f"[cyan]{query.id}[/cyan] / {model_name} / {mode}",
                )
                record: Optional[BenchmarkRecord] = None
                for bench_attempt in range(2):
                    try:
                        record = _run_single(query, model_name, mode, datasets_dir, max_attempts)
                        break
                    except httpx.HTTPStatusError as exc:
                        if exc.response.status_code == 429 and bench_attempt == 0:
                            time.sleep(30)
                            continue
                        record = _error_record(query.id, model_name, mode, str(exc))
                        break
                    except Exception as exc:
                        record = _error_record(query.id, model_name, mode, str(exc))
                        break

                if record is not None:
                    out_f.write(record.model_dump_json() + "\n")
                    out_f.flush()
                progress.advance(task)
