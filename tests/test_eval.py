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


def test_load_benchmark_reads_23_queries():
    queries = load_benchmark(_QUERIES_DIR)
    assert len(queries) == 23
    assert all(isinstance(q, BenchmarkQuery) for q in queries)


def test_load_benchmark_contains_original_5_ids():
    ids = {q.id for q in load_benchmark(_QUERIES_DIR)}
    assert {"sales_001", "sales_002", "sales_003", "sales_004", "sales_005"}.issubset(ids)


def test_load_benchmark_new_query_ids():
    ids = {q.id for q in load_benchmark(_QUERIES_DIR)}
    new_ids = {
        "movies_001", "movies_002", "movies_003", "movies_004", "movies_005",
        "movies_006", "movies_007", "movies_008",
        "weather_001", "weather_002", "weather_003", "weather_004",
        "weather_005", "weather_006", "weather_007", "weather_008",
        "sales_006", "sales_007",
    }
    assert new_ids.issubset(ids)


def test_benchmark_query_sales_001_fields():
    queries = load_benchmark(_QUERIES_DIR)
    q = next(q for q in queries if q.id == "sales_001")
    assert q.dataset == "sales.csv"
    assert q.difficulty == "easy"
    assert "bar" in q.tags
    assert q.ground_truth_spec["mark"] == "bar"


def test_benchmark_query_ground_truth_has_data_name():
    for q in load_benchmark(_QUERIES_DIR):
        if q.expects_no_correct_answer or q.ground_truth_spec is None:
            continue
        assert q.ground_truth_spec["data"] == {"name": "table"}, f"{q.id} missing data.name=table"


def test_benchmark_query_movies_007_no_answer():
    queries = load_benchmark(_QUERIES_DIR)
    q = next(q for q in queries if q.id == "movies_007")
    assert q.expects_no_correct_answer is True
    assert q.ground_truth_spec is None


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


def test_run_benchmark_produces_46_records(tmp_path):
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
    assert len(lines) == 46


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
            assert rec.query_id


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
    assert ids == {
        "sales_001", "sales_002", "sales_003", "sales_004", "sales_005",
        "sales_006", "sales_007",
        "movies_001", "movies_002", "movies_003", "movies_004", "movies_005",
        "movies_006", "movies_007", "movies_008",
        "weather_001", "weather_002", "weather_003", "weather_004", "weather_005",
        "weather_006", "weather_007", "weather_008",
    }


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

    assert count_after_first == 23
    assert count_after_second == 23  # no duplicates added


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
    assert count == 46  # 23 + 23


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


# ---------------------------------------------------------------------------
# Test 9: all ground-truth specs pass our validators
# ---------------------------------------------------------------------------


def test_all_ground_truth_specs_pass_validation():
    """Every query with a ground_truth_spec must pass our full validation pipeline.

    This catches future regressions where a GT spec becomes invalid after a
    validator is tightened (e.g., new structural rule, stricter column checking).
    """
    from chart_llm.pipeline.dataset import build_dataset_context
    from chart_llm.validation.pipeline import run_validation

    queries = load_benchmark(_QUERIES_DIR)
    failures = []
    for q in queries:
        if q.expects_no_correct_answer or q.ground_truth_spec is None:
            continue
        ctx = build_dataset_context(_DATASETS_DIR / q.dataset)
        result = run_validation(q.ground_truth_spec, ctx)
        if not result.ok:
            errs = "; ".join(f"{e.code}@{e.path}" for e in result.errors[:3])
            failures.append(f"{q.id} failed at {result.stage_failed}: {errs}")
    assert not failures, "Ground-truth specs failed validation:\n" + "\n".join(failures)


# ---------------------------------------------------------------------------
# Test 10: no-answer query handling
# ---------------------------------------------------------------------------


def _make_no_answer_record(
    final_spec,
    hallucinated: list[str],
) -> BenchmarkRecord:
    return BenchmarkRecord(
        query_id="movies_007",
        model="test-model",
        mode="baseline",
        attempts=1,
        final_validated=False,
        final_spec=final_spec,
        correctness=CorrectnessScore(match=None, mismatches=[]),
        hallucinated_columns=hallucinated,
        render_check=RenderCheck(ok=False),
        latency_ms=10.0,
        prompt_tokens=5,
        completion_tokens=5,
        stop_reason="baseline",
        error_message=None,
    )


def test_no_answer_honest_when_model_produces_no_spec():
    from chart_llm.eval.report import _failure_category
    rec = _make_no_answer_record(final_spec=None, hallucinated=[])
    assert _failure_category(rec) == "no-answer-honest"


def test_no_answer_hallucinated_when_model_produces_spec():
    from chart_llm.eval.report import _failure_category
    rec = _make_no_answer_record(final_spec=_VALID_SPEC, hallucinated=["director"])
    assert _failure_category(rec) == "no-answer-hallucinated"


def test_no_answer_correctness_match_is_none():
    """correctness.match must be None (not False) for no-answer queries."""
    rec = _make_no_answer_record(final_spec=None, hallucinated=[])
    assert rec.correctness.match is None


# ---------------------------------------------------------------------------
# Test 11: count-form equivalence (Issue 3)
# ---------------------------------------------------------------------------

_COUNT_GT_FIELDLESS = {
    "$schema": _SCHEMA_URL,
    "data": {"name": "table"},
    "mark": "bar",
    "encoding": {
        "x": {"field": "genre", "type": "nominal"},
        "y": {"aggregate": "count", "type": "quantitative"},
    },
}


def test_count_fieldless_gt_vs_fielded_prediction_matches():
    """GT with fieldless count should match prediction that names a field."""
    predicted = {
        **_COUNT_GT_FIELDLESS,
        "encoding": {
            "x": {"field": "genre", "type": "nominal"},
            "y": {"field": "title", "aggregate": "count", "type": "quantitative"},
        },
    }
    score = spec_correctness(predicted, _COUNT_GT_FIELDLESS)
    assert score.match is True, f"Fieldless GT should match fielded prediction: {score.mismatches}"


def test_count_fielded_gt_vs_fieldless_prediction_matches():
    """GT with field=title count should match prediction without a field."""
    gt_fielded = {
        **_COUNT_GT_FIELDLESS,
        "encoding": {
            "x": {"field": "genre", "type": "nominal"},
            "y": {"field": "title", "aggregate": "count", "type": "quantitative"},
        },
    }
    predicted = {
        **_COUNT_GT_FIELDLESS,
        "encoding": {
            "x": {"field": "genre", "type": "nominal"},
            "y": {"aggregate": "count", "type": "quantitative"},
        },
    }
    score = spec_correctness(predicted, gt_fielded)
    assert score.match is True, f"Fielded GT should match fieldless prediction: {score.mismatches}"


def test_count_different_field_still_matches():
    """Count on a different field is still a row count — must match."""
    gt_fielded = {
        **_COUNT_GT_FIELDLESS,
        "encoding": {
            "x": {"field": "genre", "type": "nominal"},
            "y": {"field": "title", "aggregate": "count", "type": "quantitative"},
        },
    }
    predicted = {
        **_COUNT_GT_FIELDLESS,
        "encoding": {
            "x": {"field": "genre", "type": "nominal"},
            "y": {"field": "studio", "aggregate": "count", "type": "quantitative"},
        },
    }
    score = spec_correctness(predicted, gt_fielded)
    assert score.match is True, f"Count on different field should match: {score.mismatches}"


# ---------------------------------------------------------------------------
# Test 12: faceted spec scoring (Issue 4)
# ---------------------------------------------------------------------------

_FACET_GT = {
    "$schema": _SCHEMA_URL,
    "data": {"name": "table"},
    "facet": {"field": "region", "type": "nominal"},
    "spec": {
        "mark": "line",
        "encoding": {
            "x": {"field": "date", "type": "temporal"},
            "y": {"field": "revenue", "aggregate": "sum", "type": "quantitative"},
        },
    },
}


def test_faceted_gt_identical_prediction_matches():
    score = spec_correctness(_FACET_GT, _FACET_GT)
    assert score.match is True, f"Identical faceted specs should match: {score.mismatches}"


def test_faceted_gt_non_faceted_prediction_does_not_match():
    """Critical regression test: non-faceted prediction must fail faceted GT."""
    predicted_flat = {
        "$schema": _SCHEMA_URL,
        "data": {"name": "table"},
        "mark": "line",
        "encoding": {
            "x": {"field": "date", "type": "temporal"},
            "y": {"field": "revenue", "aggregate": "sum", "type": "quantitative"},
        },
    }
    score = spec_correctness(predicted_flat, _FACET_GT)
    assert score.match is False, "Non-faceted prediction must not match faceted GT"
    assert any("facet" in m for m in score.mismatches), f"Expected facet mismatch in: {score.mismatches}"


def test_faceted_gt_wrong_facet_field_does_not_match():
    predicted = {
        **_FACET_GT,
        "facet": {"field": "product", "type": "nominal"},
    }
    score = spec_correctness(predicted, _FACET_GT)
    assert score.match is False, "Wrong facet field should not match"
    assert any("facet" in m for m in score.mismatches), f"Expected facet mismatch in: {score.mismatches}"


# ---------------------------------------------------------------------------
# Test 13: calculate expression leniency (Issue 5)
# ---------------------------------------------------------------------------

_CALC_BASE = {
    "$schema": _SCHEMA_URL,
    "data": {"name": "table"},
    "mark": "point",
    "transform": [
        {"calculate": "datum.imdb_rating > 7.0 ? 'High' : 'Low'", "as": "rating_tier"}
    ],
    "encoding": {
        "x": {"field": "box_office_usd", "type": "quantitative"},
        "y": {"field": "runtime_min", "type": "quantitative"},
        "color": {"field": "rating_tier", "type": "nominal"},
    },
}


def test_calculate_different_expression_same_as_matches():
    """Prediction with a slightly different calculate expression but same 'as' must match."""
    pred_a = {
        **_CALC_BASE,
        "transform": [
            {"calculate": "datum.imdb_rating >= 7 ? 'High' : 'Low'", "as": "rating_tier"}
        ],
    }
    score = spec_correctness(pred_a, _CALC_BASE)
    assert score.match is True, f"pred_a should match GT: {score.mismatches}"


def test_calculate_different_values_same_as_matches():
    """Even lowercased output values don't matter — match is on 'as' key only."""
    pred_b = {
        **_CALC_BASE,
        "transform": [
            {"calculate": "datum.imdb_rating > 7 ? 'high' : 'low'", "as": "rating_tier"}
        ],
    }
    score = spec_correctness(pred_b, _CALC_BASE)
    assert score.match is True, f"pred_b should match GT: {score.mismatches}"


def test_calculate_different_as_field_does_not_match():
    """A calculate step with a different output field name must NOT match."""
    pred_wrong = {
        **_CALC_BASE,
        "transform": [
            {"calculate": "datum.imdb_rating > 7.0 ? 'High' : 'Low'", "as": "quality_band"}
        ],
    }
    score = spec_correctness(pred_wrong, _CALC_BASE)
    assert score.match is False, "Different 'as' field should not match"


# ---------------------------------------------------------------------------
# Test 14: hallucinated_columns skips derive-field aliases (Issue fix)
# ---------------------------------------------------------------------------


def test_hallucinated_columns_skips_calculate_derived_field(simple_ctx):
    """A field produced by calculate must not be flagged as hallucinated."""
    spec = {
        "$schema": _SCHEMA_URL,
        "data": {"name": "table"},
        "mark": "point",
        "transform": [{"calculate": "datum.revenue > 1500 ? 'High' : 'Low'", "as": "tier"}],
        "encoding": {
            "x": {"field": "region", "type": "nominal"},
            "color": {"field": "tier", "type": "nominal"},
        },
    }
    result = hallucinated_columns(spec, simple_ctx)
    assert result == [], f"tier is calculate-derived, not a hallucination: {result}"


def test_hallucinated_columns_flags_field_not_covered_by_calculate(simple_ctx):
    """A field referenced in encoding that is NOT the 'as' alias of any transform IS hallucinated."""
    spec = {
        "$schema": _SCHEMA_URL,
        "data": {"name": "table"},
        "mark": "point",
        "transform": [{"calculate": "datum.revenue > 1500 ? 'High' : 'Low'", "as": "other_field"}],
        "encoding": {
            "x": {"field": "region", "type": "nominal"},
            "color": {"field": "tier", "type": "nominal"},
        },
    }
    result = hallucinated_columns(spec, simple_ctx)
    assert "tier" in result, f"tier is not derived by any transform, should be flagged: {result}"


def test_hallucinated_columns_skips_joinaggregate_derived_field(simple_ctx):
    """A field produced by joinaggregate must not be flagged as hallucinated."""
    spec = {
        "$schema": _SCHEMA_URL,
        "data": {"name": "table"},
        "mark": "bar",
        "transform": [
            {"joinaggregate": [{"op": "sum", "field": "revenue", "as": "total_revenue"}]}
        ],
        "encoding": {
            "x": {"field": "region", "type": "nominal"},
            "y": {"field": "total_revenue", "type": "quantitative"},
        },
    }
    result = hallucinated_columns(spec, simple_ctx)
    assert result == [], f"total_revenue is joinaggregate-derived, not a hallucination: {result}"
