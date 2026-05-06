"""Build a Markdown benchmark report from a JSONL results file."""

import json
import statistics
import subprocess
from pathlib import Path
from typing import Optional

from chart_llm.eval.runner import BenchmarkRecord
from chart_llm.eval.scoring import CorrectnessScore, RenderCheck


# ---------------------------------------------------------------------------
# Reading / parsing
# ---------------------------------------------------------------------------


def _read_records(jsonl_path: Path) -> list[BenchmarkRecord]:
    records: list[BenchmarkRecord] = []
    for line in jsonl_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            records.append(BenchmarkRecord.model_validate_json(line))
        except Exception:
            pass
    return records


def _git_sha() -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.stdout.strip() or "unknown"
    except Exception:
        return "unknown"


def _schema_version() -> str:
    try:
        from chart_llm.validation.schema import _CACHE_PATH

        if _CACHE_PATH.exists():
            data = json.loads(_CACHE_PATH.read_text())
            return data.get("title", "Vega-Lite v5")
    except Exception:
        pass
    return "Vega-Lite v5"


# ---------------------------------------------------------------------------
# Metrics helpers
# ---------------------------------------------------------------------------


def _pct(values: list[bool]) -> str:
    if not values:
        return "—"
    return f"{sum(values) / len(values) * 100:.0f}%"


def _median_ms(values: list[float]) -> str:
    if not values:
        return "—"
    return f"{statistics.median(values):.0f} ms"


def _avg_attempts(values: list[int]) -> str:
    if not values:
        return "—"
    return f"{sum(values) / len(values):.2f}"


def _delta_str(base: Optional[float], val: Optional[float]) -> str:
    if base is None or val is None:
        return "—"
    d = val - base
    sign = "↑" if d > 0 else ("↓" if d < 0 else "")
    return f"{sign}{abs(d):.0f}%"


def _failure_category(rec: BenchmarkRecord) -> str:
    if rec.error_message:
        return "generation_error"
    if rec.final_spec is None:
        return "no_spec"
    if not rec.render_check.ok:
        return "render_failed"
    if not rec.correctness.match:
        for m in rec.correctness.mismatches:
            if "mark mismatch" in m:
                return "wrong_mark"
            if "aggregate" in m:
                return "wrong_aggregate"
            if "transform" in m:
                return "wrong_transform"
            if "encoding" in m:
                return "wrong_encoding"
        return "wrong_encoding"
    return "correct"


# ---------------------------------------------------------------------------
# Report builder
# ---------------------------------------------------------------------------


def build_report(jsonl_path: Path, out_md_path: Path) -> None:
    """Read jsonl_path and write a Markdown report to out_md_path."""
    records = _read_records(jsonl_path)
    lines: list[str] = []

    def h(level: int, text: str) -> None:
        lines.append(f"{'#' * level} {text}")
        lines.append("")

    def row(*cells: str) -> str:
        return "| " + " | ".join(str(c) for c in cells) + " |"

    def sep(*n: int) -> str:
        return "| " + " | ".join("-" * max(k, 3) for k in n) + " |"

    # ── Title ────────────────────────────────────────────────────────────────

    h(1, "Benchmark Report")

    all_models = sorted({r.model for r in records})
    all_modes = sorted({r.mode for r in records})
    query_ids = sorted({r.query_id for r in records})

    # ── Summary ──────────────────────────────────────────────────────────────

    h(2, "Summary")
    lines.append(row("Model", "Mode", "Queries", "Succeeded", "Errored"))
    lines.append(sep(20, 12, 7, 10, 8))
    for model in all_models:
        for mode in all_modes:
            subset = [r for r in records if r.model == model and r.mode == mode]
            if not subset:
                continue
            succeeded = sum(1 for r in subset if r.error_message is None)
            errored = sum(1 for r in subset if r.error_message is not None)
            lines.append(row(model, mode, len(subset), succeeded, errored))
    lines.append("")

    # ── Results ──────────────────────────────────────────────────────────────

    h(2, "Results")
    lines.append(
        row("Model", "Mode", "Validated", "Correctness", "No Hallucinations", "Renders", "Median Latency", "Avg Attempts")
    )
    lines.append(sep(20, 12, 10, 12, 18, 8, 15, 13))
    for model in all_models:
        for mode in all_modes:
            subset = [r for r in records if r.model == model and r.mode == mode]
            if not subset:
                continue
            lines.append(
                row(
                    model,
                    mode,
                    _pct([r.final_validated for r in subset]),
                    _pct([r.correctness.match for r in subset]),
                    _pct([r.hallucinated_columns == [] for r in subset]),
                    _pct([r.render_check.ok for r in subset]),
                    _median_ms([r.latency_ms for r in subset]),
                    _avg_attempts([r.attempts for r in subset]),
                )
            )
    lines.append("")

    # ── Validation Impact ─────────────────────────────────────────────────────

    h(2, "Validation Impact")
    lines.append(row("Model", "Validated Δ", "Correctness Δ", "No Hallucinations Δ", "Renders Δ"))
    lines.append(sep(20, 12, 14, 20, 10))

    def _rate(recs: list[BenchmarkRecord], attr: str) -> Optional[float]:
        if not recs:
            return None
        if attr == "validated":
            vals = [r.final_validated for r in recs]
        elif attr == "correctness":
            vals = [r.correctness.match for r in recs]
        elif attr == "no_hall":
            vals = [r.hallucinated_columns == [] for r in recs]
        elif attr == "renders":
            vals = [r.render_check.ok for r in recs]
        else:
            return None
        return sum(vals) / len(vals) * 100

    for model in all_models:
        base = [r for r in records if r.model == model and r.mode == "baseline"]
        val = [r for r in records if r.model == model and r.mode == "validated"]
        if not base or not val:
            continue
        lines.append(
            row(
                model,
                _delta_str(_rate(base, "validated"), _rate(val, "validated")),
                _delta_str(_rate(base, "correctness"), _rate(val, "correctness")),
                _delta_str(_rate(base, "no_hall"), _rate(val, "no_hall")),
                _delta_str(_rate(base, "renders"), _rate(val, "renders")),
            )
        )
    lines.append("")

    # ── Failure-Mode Taxonomy ────────────────────────────────────────────────

    h(2, "Failure-Mode Taxonomy")
    from collections import Counter

    counts: Counter[str] = Counter(_failure_category(r) for r in records)
    lines.append(row("Category", "Count"))
    lines.append(sep(25, 6))
    for category, count in counts.most_common(10):
        lines.append(row(category, count))
    lines.append("")

    # ── Per-Query Details ────────────────────────────────────────────────────

    h(2, "Per-Query Details")
    for qid in query_ids:
        q_records = [r for r in records if r.query_id == qid]
        if not q_records:
            continue
        # Get question from first record — not stored; just use the query_id as label
        lines.append(f"### {qid}")
        lines.append("")
        lines.append(row("Model", "Mode", "Validated", "Correct", "Hallucinations", "Renders", "Latency"))
        lines.append(sep(20, 12, 10, 8, 14, 8, 10))
        for r in sorted(q_records, key=lambda x: (x.model, x.mode)):
            lines.append(
                row(
                    r.model,
                    r.mode,
                    "✓" if r.final_validated else "✗",
                    "✓" if r.correctness.match else "✗",
                    str(r.hallucinated_columns) if r.hallucinated_columns else "none",
                    "✓" if r.render_check.ok else "✗",
                    f"{r.latency_ms:.0f} ms",
                )
            )
        lines.append("")

    # ── Reproducibility ──────────────────────────────────────────────────────

    h(2, "Reproducibility")
    lines.append(f"- **Queries:** {len(query_ids)}")
    lines.append(f"- **Models:** {', '.join(all_models)}")
    lines.append(f"- **Vega-Lite schema:** {_schema_version()}")
    lines.append(f"- **Git SHA:** {_git_sha()}")
    lines.append(f"- **Total records:** {len(records)}")
    lines.append("")

    out_md_path.write_text("\n".join(lines), encoding="utf-8")
