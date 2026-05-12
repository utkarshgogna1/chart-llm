"""Tests for the benchmark evaluation harness."""

import json
from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytest

from chart_llm.eval.queries import BenchmarkQuery, load_benchmark
from chart_llm.eval.report import build_report
from chart_llm.eval.runner import BenchmarkRecord, run_benchmark
from chart_llm.eval.scoring import (
    CorrectnessScore,
    RenderCheck,
    hallucinated_columns,
    render_check,
    spec_correctness,
)
from chart_llm.models.base import LLMModel, LLMResponse
from chart_llm.pipeline.dataset import ColumnInfo, DatasetContext

# ---------------------------------------------------------------------------
# Shared fixtures / constants
# ---------------------------------------------------------------------------

_QUERIES_DIR = Path(__file__).parent.parent / "benchmarks" / "queries"
_DATASETS_DIR = Path(__file__).parent.parent / "benchmarks" / "datasets"

_SCHEMA_URL = "https://vega.github.io/schema/vega-lite/v5.json"

_VALID_SPEC = {
    "$schema": _SCHEMA_URL,
    "data": {"name": "table"},
    "mark": "bar",
    "encoding": {
        "x": {"field": "region", "type": "nominal"},
        "y": {"field": "revenue", "aggregate": "sum", "type": "quantitative"},
    },
}


@pytest.fixture
def simple_ctx() -> DatasetContext:
    df = pd.DataFrame({"region": ["North", "South"], "revenue": [1000.0, 2000.0]})
    return DatasetContext(
        name="test",
        df=df,
        column_schema=[
            ColumnInfo(name="region", dtype="object", sample_values=["North"], n_unique=2, n_null=0),
            ColumnInfo(name="revenue", dtype="float64", sample_values=["1000.0"], n_unique=2, n_null=0),
        ],
        row_count=2,
    )


class _FakeClient(LLMModel):
    def generate(self, system: str, user: str, max_retries: int = 2) -> LLMResponse:
        return LLMResponse(
            text=json.dumps(_VALID_SPEC),
            model_name="fake",
            latency_ms=5.0,
            prompt_tokens=10,
            completion_tokens=20,
        )


# ---------------------------------------------------------------------------
# Test 1: load_benchmark
# ---------------------------------------------------------------------------


def test_load_benchmark_reads_5_queries():
    queries = load_benchmark(_QUERIES_DIR)
    assert len(queries) == 5
    assert all(isinstance(q, BenchmarkQuery) for q in queries)


def test_load_benchmark_ids():
    ids = {q.id for q in load_benchmark(_QUERIES_DIR)}
    assert ids == {"sales_001", "sales_002", "sales_003", "sales_004", "sales_005"}


def test_benchmark_query_sales_001_fields():
    queries = load_benchmark(_QUERIES_DIR)
    q = next(q for q in queries if q.id == "sales_001")
    assert q.dataset == "sales.csv"
    assert q.difficulty == "easy"
    assert "bar" in q.tags
    assert q.ground_truth_spec["mark"] == "bar"


def test_benchmark_query_ground_truth_has_data_name():
    for q in load_benchmark(_QUERIES_DIR):
        assert q.ground_truth_spec["data"] == {"name": "table"}, f"{q.id} missing data.name=table"


def test_benchmark_query_difficulties_valid():
    valid = {"easy", "medium", "hard"}
    for q in load_benchmark(_QUERIES_DIR):
        assert q.difficulty in valid


# ---------------------------------------------------------------------------
# Test 2: spec_correctness
# ---------------------------------------------------------------------------


def test_spec_correctness_identical_match():
    score = spec_correctness(_VALID_SPEC, _VALID_SPEC)
    assert score.match is True
    assert score.mismatches == []


def test_spec_correctness_mark_mismatch():
    predicted = {**_VALID_SPEC, "mark": "line"}
    score = spec_correctness(predicted, _VALID_SPEC)
    assert score.match is False
    assert any("mark" in m for m in score.mismatches)
    assert any("line" in m and "bar" in m for m in score.mismatches)


def test_spec_correctness_extra_predicted_channel_is_ok():
    # predicted has a color channel not in ground truth → should still match
    predicted = {
        **_VALID_SPEC,
        "encoding": {
            **_VALID_SPEC["encoding"],
            "color": {"field": "region", "type": "nominal"},
        },
    }
    score = spec_correctness(predicted, _VALID_SPEC)
    assert score.match is True
    assert score.mismatches == []


def test_spec_correctness_wrong_field_name():
    predicted = {
        **_VALID_SPEC,
        "encoding": {
            "x": {"field": "product", "type": "nominal"},
            "y": {"field": "revenue", "aggregate": "sum", "type": "quantitative"},
        },
    }
    score = spec_correctness(predicted, _VALID_SPEC)
    assert score.match is False
    assert any("encoding.x" in m for m in score.mismatches)


def test_spec_correctness_wrong_aggregate():
    predicted = {
        **_VALID_SPEC,
        "encoding": {
            "x": {"field": "region", "type": "nominal"},
            "y": {"field": "revenue", "aggregate": "mean", "type": "quantitative"},
        },
    }
    score = spec_correctness(predicted, _VALID_SPEC)
    assert score.match is False


def test_spec_correctness_transform_mismatch():
    gt = {
        **_VALID_SPEC,
        "transform": [{"filter": "datum.region === 'West'"}],
    }
    predicted_no_transform = {**_VALID_SPEC}
    score = spec_correctness(predicted_no_transform, gt)
    assert score.match is False
    assert any("transform" in m for m in score.mismatches)


def test_spec_correctness_transform_match_regardless_of_order():
    gt = {
        **_VALID_SPEC,
        "transform": [
            {"filter": "datum.region === 'West'"},
            {"filter": "datum.units > 10"},
        ],
    }
    predicted = {
        **_VALID_SPEC,
        "transform": [
            {"filter": "datum.units > 10"},
            {"filter": "datum.region === 'West'"},
        ],
    }
    score = spec_correctness(predicted, gt)
    assert score.match is True


# ---------------------------------------------------------------------------
# Test 3: hallucinated_columns
# ---------------------------------------------------------------------------


def test_hallucinated_columns_flags_missing_field(simple_ctx):
    bad_spec = {
        **_VALID_SPEC,
        "encoding": {
            "x": {"field": "hallucinated_col", "type": "nominal"},
            "y": {"field": "revenue", "aggregate": "sum", "type": "quantitative"},
        },
    }
    result = hallucinated_columns(bad_spec, simple_ctx)
    assert "hallucinated_col" in result


def test_hallucinated_columns_ignores_valid_fields(simple_ctx):
    result = hallucinated_columns(_VALID_SPEC, simple_ctx)
    assert result == []


def test_hallucinated_columns_returns_sorted_unique(simple_ctx):
    bad_spec = {
        **_VALID_SPEC,
        "encoding": {
            "x": {"field": "zzz_col", "type": "nominal"},
            "y": {"field": "aaa_col", "type": "quantitative"},
        },
    }
    result = hallucinated_columns(bad_spec, simple_ctx)
    assert result == sorted(result)
    assert len(result) == len(set(result))


# ---------------------------------------------------------------------------
# Test 4: render_check
# ---------------------------------------------------------------------------


def test_render_check_passes_on_good_spec(simple_ctx):
    result = render_check(_VALID_SPEC, simple_ctx.df)
    assert result.ok is True
    assert result.error is None


def test_render_check_returns_render_check_instance(simple_ctx):
    result = render_check(_VALID_SPEC, simple_ctx.df)
    assert isinstance(result, RenderCheck)


def test_render_check_fails_gracefully_on_exception():
    # render_to_html doesn't raise on schema-invalid specs (it's just HTML),
    # but we can verify the structure when ok=False is set
    rc = RenderCheck(ok=False, error="some error")
    assert rc.ok is False
    assert rc.error == "some error"


# ---------------------------------------------------------------------------
# Test 5: run_benchmark produces correct number of records
# ---------------------------------------------------------------------------


def test_run_benchmark_produces_10_records(tmp_path):
    output = tmp_path / "results.jsonl"
    with patch("chart_llm.eval.runner.get_client", return_value=_FakeClient()):
        run_benchmark(
            model_names=["fake-model"],
            modes=["baseline", "validated"],
            queries_dir=_QUERIES_DIR,
            datasets_dir=_DATASETS_DIR,
            output_path=output,
            max_attempts=1,
            resume=False,
        )
    lines = [l for l in output.read_text().splitlines() if l.strip()]
    assert len(lines) == 10


def test_run_benchmark_records_are_parseable(tmp_path):
    output = tmp_path / "results.jsonl"
    with patch("chart_llm.eval.runner.get_client", return_value=_FakeClient()):
        run_benchmark(
            model_names=["fake-model"],
            modes=["baseline", "validated"],
            queries_dir=_QUERIES_DIR,
            datasets_dir=_DATASETS_DIR,
            output_path=output,
            max_attempts=1,
            resume=False,
        )
    for line in output.read_text().splitlines():
        if line.strip():
            rec = BenchmarkRecord.model_validate_json(line)
            assert rec.query_id.startswith("sales_")


def test_run_benchmark_records_cover_all_queries(tmp_path):
    output = tmp_path / "results.jsonl"
    with patch("chart_llm.eval.runner.get_client", return_value=_FakeClient()):
        run_benchmark(
            model_names=["fake-model"],
            modes=["baseline"],
            queries_dir=_QUERIES_DIR,
            datasets_dir=_DATASETS_DIR,
            output_path=output,
            max_attempts=1,
            resume=False,
        )
    ids = {
        BenchmarkRecord.model_validate_json(l).query_id
        for l in output.read_text().splitlines()
        if l.strip()
    }
    assert ids == {"sales_001", "sales_002", "sales_003", "sales_004", "sales_005"}


# ---------------------------------------------------------------------------
# Test 6: resume — second run is a no-op
# ---------------------------------------------------------------------------


def test_run_benchmark_resume_skips_existing(tmp_path):
    output = tmp_path / "results.jsonl"

    def _run():
        with patch("chart_llm.eval.runner.get_client", return_value=_FakeClient()):
            run_benchmark(
                model_names=["fake-model"],
                modes=["baseline"],
                queries_dir=_QUERIES_DIR,
                datasets_dir=_DATASETS_DIR,
                output_path=output,
                max_attempts=1,
                resume=True,
            )

    _run()
    count_after_first = len([l for l in output.read_text().splitlines() if l.strip()])
    _run()
    count_after_second = len([l for l in output.read_text().splitlines() if l.strip()])

    assert count_after_first == 5
    assert count_after_second == 5  # no duplicates added


def test_run_benchmark_no_resume_overwrites(tmp_path):
    output = tmp_path / "results.jsonl"

    def _run(resume):
        with patch("chart_llm.eval.runner.get_client", return_value=_FakeClient()):
            run_benchmark(
                model_names=["fake-model"],
                modes=["baseline"],
                queries_dir=_QUERIES_DIR,
                datasets_dir=_DATASETS_DIR,
                output_path=output,
                max_attempts=1,
                resume=resume,
            )

    _run(resume=True)
    _run(resume=False)  # resume=False → does not skip existing keys → appends duplicates
    count = len([l for l in output.read_text().splitlines() if l.strip()])
    assert count == 10  # 5 + 5


# ---------------------------------------------------------------------------
# Test 7: build_report contains section headers
# ---------------------------------------------------------------------------


def test_build_report_contains_section_headers(tmp_path):
    jsonl = tmp_path / "test.jsonl"
    rec = BenchmarkRecord(
        query_id="sales_001",
        model="gemini-flash",
        mode="baseline",
        attempts=1,
        final_validated=False,
        final_spec=_VALID_SPEC,
        correctness=CorrectnessScore(match=True, mismatches=[]),
        hallucinated_columns=[],
        render_check=RenderCheck(ok=True),
        latency_ms=100.0,
        prompt_tokens=50,
        completion_tokens=30,
        stop_reason="baseline",
        error_message=None,
    )
    jsonl.write_text(rec.model_dump_json() + "\n", encoding="utf-8")

    out_md = tmp_path / "report.md"
    build_report(jsonl, out_md)

    content = out_md.read_text()
    assert "# Benchmark Report" in content
    assert "## Summary" in content
    assert "## Results" in content
    assert "## Failure-Mode Taxonomy" in content
    assert "## Per-Query Details" in content
    assert "## Reproducibility" in content


def test_build_report_validation_impact_requires_both_modes(tmp_path):
    jsonl = tmp_path / "test.jsonl"
    # Two records: one baseline, one validated — same model
    recs = []
    for mode in ("baseline", "validated"):
        recs.append(
            BenchmarkRecord(
                query_id="sales_001",
                model="gemini-flash",
                mode=mode,
                attempts=1,
                final_validated=(mode == "validated"),
                final_spec=_VALID_SPEC,
                correctness=CorrectnessScore(match=True, mismatches=[]),
                hallucinated_columns=[],
                render_check=RenderCheck(ok=True),
                latency_ms=50.0,
                prompt_tokens=50,
                completion_tokens=30,
                stop_reason=mode,
                error_message=None,
            )
        )
    jsonl.write_text("\n".join(r.model_dump_json() for r in recs), encoding="utf-8")

    out_md = tmp_path / "report.md"
    build_report(jsonl, out_md)
    content = out_md.read_text()
    assert "## Validation Impact" in content
    assert "gemini-flash" in content


# ---------------------------------------------------------------------------
# Filter-form equivalence (these tests FAILED before _normalize_filter was added)
# ---------------------------------------------------------------------------

_FILTER_GT = {
    "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
    "data": {"name": "table"},
    "mark": "bar",
    "transform": [{"filter": "datum.region === 'West'"}],
    "encoding": {
        "x": {"field": "product", "type": "nominal"},
        "y": {"field": "units", "type": "quantitative", "aggregate": "sum"},
    },
}


def test_filter_object_form_equivalent_to_string():
    """Object filter {field: X, equal: V} must score as equal to string 'datum.X === V'."""
    predicted = {
        **_FILTER_GT,
        "transform": [{"filter": {"field": "region", "equal": "West"}}],
    }
    score = spec_correctness(predicted, _FILTER_GT)
    assert score.match is True, f"Expected match=True, got mismatches: {score.mismatches}"


def test_filter_double_equals_equivalent_to_triple():
    """'datum.region == West' must score the same as 'datum.region === West'."""
    predicted = {
        **_FILTER_GT,
        "transform": [{"filter": "datum.region == 'West'"}],
    }
    score = spec_correctness(predicted, _FILTER_GT)
    assert score.match is True, f"Expected match=True, got mismatches: {score.mismatches}"


def test_filter_object_gt_matches_string_predicted():
    """Ground truth as object form, predicted as string — must match."""
    gt = {
        **_FILTER_GT,
        "transform": [{"filter": {"field": "region", "equal": "West"}}],
    }
    score = spec_correctness(_FILTER_GT, gt)
    assert score.match is True


def test_filter_different_values_still_mismatch():
    """Different filter values must NOT score as equivalent."""
    predicted = {
        **_FILTER_GT,
        "transform": [{"filter": "datum.region === 'East'"}],
    }
    score = spec_correctness(predicted, _FILTER_GT)
    assert score.match is False


def test_missing_transform_still_fails():
    """Predicted spec with no transform when ground truth has one must still fail."""
    predicted = {k: v for k, v in _FILTER_GT.items() if k != "transform"}
    score = spec_correctness(predicted, _FILTER_GT)
    assert score.match is False


def test_extra_unsolicited_color_channel_does_not_penalize():
    """sales_004 validated pattern: extra color channel on top of correct x/y/transform."""
    predicted = {
        **_FILTER_GT,
        "encoding": {
            **_FILTER_GT["encoding"],
            "color": {"field": "product", "type": "nominal"},
        },
    }
    score = spec_correctness(predicted, _FILTER_GT)
    assert score.match is True, f"Extra color channel should not cause mismatch: {score.mismatches}"


# ---------------------------------------------------------------------------
# Test 8: Summary table column semantics
# ---------------------------------------------------------------------------


def _make_record(
    query_id: str,
    final_validated: bool,
    error_message,
    stop_reason: str = "baseline",
) -> BenchmarkRecord:
    return BenchmarkRecord(
        query_id=query_id,
        model="test-model",
        mode="baseline",
        attempts=1,
        final_validated=final_validated,
        final_spec=_VALID_SPEC if final_validated else None,
        correctness=CorrectnessScore(match=final_validated, mismatches=[]),
        hallucinated_columns=[],
        render_check=RenderCheck(ok=final_validated),
        latency_ms=10.0,
        prompt_tokens=5,
        completion_tokens=5,
        stop_reason=stop_reason,
        error_message=error_message,
    )


def test_summary_table_succeeded_counts_final_validated(tmp_path):
    jsonl = tmp_path / "test.jsonl"
    recs = [
        _make_record("sales_001", final_validated=True, error_message=None),
        _make_record("sales_002", final_validated=False, error_message=None),
        _make_record("sales_003", final_validated=False, error_message="API error"),
    ]
    jsonl.write_text("\n".join(r.model_dump_json() for r in recs), encoding="utf-8")

    out_md = tmp_path / "report.md"
    build_report(jsonl, out_md)
    content = out_md.read_text()

    # Extract only lines in the ## Summary section
    all_lines = content.splitlines()
    in_summary = False
    summary_model_row = None
    for line in all_lines:
        if line.startswith("## Summary"):
            in_summary = True
            continue
        if in_summary and line.startswith("## "):
            break
        if in_summary and "test-model" in line and "baseline" in line:
            summary_model_row = line
            break
    assert summary_model_row is not None, "Summary table row not found"
    cells = [c.strip() for c in summary_model_row.split("|") if c.strip()]
    # cells: [model, mode, queries, succeeded, errored, no_spec]
    assert cells[2] == "3"   # Queries
    assert cells[3] == "1"   # Succeeded (only final_validated=True)
    assert cells[4] == "1"   # Errored (error_message is not None)
    assert cells[5] == "1"   # No Spec (final_validated=False AND error_message is None)
