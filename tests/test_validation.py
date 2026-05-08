"""Comprehensive tests for all four validators and the pipeline orchestrator."""

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from chart_llm.pipeline.dataset import ColumnInfo, DatasetContext
from chart_llm.validation.columns import validate_columns
from chart_llm.validation.data_ref import validate_data_ref
from chart_llm.validation.pipeline import run_validation
from chart_llm.validation.schema import validate_schema
from chart_llm.validation.semantics import validate_semantics
from chart_llm.validation.types import ValidationResult

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_SCHEMA_URL = "https://vega.github.io/schema/vega-lite/v5.json"

_VALID_SPEC = {
    "$schema": _SCHEMA_URL,
    "data": {"name": "table"},
    "mark": "bar",
    "encoding": {
        "x": {"field": "region", "type": "nominal"},
        "y": {"field": "revenue", "aggregate": "sum", "type": "quantitative"},
    },
    "title": "Revenue by region",
}


@pytest.fixture
def ctx() -> DatasetContext:
    """Tiny in-memory DatasetContext — no CSV loading."""
    df = pd.DataFrame(
        {
            "region": ["North", "South", "East"],
            "revenue": [1000.0, 2000.0, 3000.0],
            "date": ["2024-01-01", "2024-01-08", "2024-01-15"],
            "units": [10, 20, 30],
        }
    )
    return DatasetContext(
        name="test",
        df=df,
        column_schema=[
            ColumnInfo(
                name="region",
                dtype="object",
                sample_values=["North", "South", "East"],
                n_unique=3,
                n_null=0,
            ),
            ColumnInfo(
                name="revenue",
                dtype="float64",
                sample_values=["1000.0", "2000.0", "3000.0"],
                n_unique=3,
                n_null=0,
            ),
            ColumnInfo(
                name="date",
                dtype="object",
                sample_values=["2024-01-01", "2024-01-08", "2024-01-15"],
                n_unique=3,
                n_null=0,
            ),
            ColumnInfo(
                name="units",
                dtype="int64",
                sample_values=["10", "20", "30"],
                n_unique=3,
                n_null=0,
            ),
        ],
        row_count=3,
    )


# ===========================================================================
# Schema validation
# ===========================================================================


class TestSchemaValidation:
    def test_valid_spec_passes(self, vega_lite_schema):
        result = validate_schema(_VALID_SPEC)
        assert isinstance(result, ValidationResult)
        assert result.ok
        assert result.errors == []

    def test_mark_as_integer_fails(self, vega_lite_schema):
        bad = {**_VALID_SPEC, "mark": 42}
        result = validate_schema(bad)
        assert not result.ok
        assert result.stage_failed == "schema"
        assert len(result.errors) >= 1

    def test_error_has_correct_stage(self, vega_lite_schema):
        bad = {**_VALID_SPEC, "mark": 99}
        result = validate_schema(bad)
        assert all(e.stage == "schema" for e in result.errors)

    def test_error_code_populated(self, vega_lite_schema):
        bad = {**_VALID_SPEC, "mark": 99}
        result = validate_schema(bad)
        assert all(isinstance(e.code, str) and e.code for e in result.errors)

    def test_caps_at_five_errors(self, vega_lite_schema):
        # Feed a completely empty object — many required fields missing
        result = validate_schema({})
        assert len(result.errors) <= 5


# ===========================================================================
# Column validation
# ===========================================================================


class TestColumnValidation:
    def test_valid_fields_pass(self, ctx):
        spec = {"encoding": {"x": {"field": "region"}, "y": {"field": "revenue"}}}
        result = validate_columns(spec, ctx)
        assert result.ok

    def test_misspelled_field_fails(self, ctx):
        spec = {"encoding": {"x": {"field": "regionn"}}}
        result = validate_columns(spec, ctx)
        assert not result.ok
        assert result.stage_failed == "columns"
        assert result.errors[0].code == "missing_column"

    def test_misspelled_field_suggestion(self, ctx):
        spec = {"encoding": {"x": {"field": "regionn"}}}
        result = validate_columns(spec, ctx)
        assert result.errors[0].suggestion is not None
        assert "region" in result.errors[0].suggestion

    def test_completely_wrong_field_no_suggestion(self, ctx):
        spec = {"encoding": {"x": {"field": "zzzznonexistent"}}}
        result = validate_columns(spec, ctx)
        assert not result.ok
        assert result.errors[0].suggestion is None

    def test_dotted_field_checks_root_only(self, ctx):
        # "address.city" — "address" is not in ctx, should fail
        spec = {"encoding": {"x": {"field": "address.city"}}}
        result = validate_columns(spec, ctx)
        assert not result.ok
        assert '"address"' in result.errors[0].message

    def test_dotted_field_valid_root_passes(self, ctx):
        # "region.subfield" — root "region" IS in ctx
        spec = {"encoding": {"x": {"field": "region.subfield"}}}
        result = validate_columns(spec, ctx)
        assert result.ok

    def test_nested_spec_fields_found(self, ctx):
        spec = {
            "layer": [
                {"encoding": {"x": {"field": "revenue"}}},
                {"encoding": {"y": {"field": "missing_col"}}},
            ]
        }
        result = validate_columns(spec, ctx)
        assert not result.ok
        assert result.errors[0].code == "missing_column"

    def test_error_path_points_to_field_key(self, ctx):
        spec = {"encoding": {"x": {"field": "regionn"}}}
        result = validate_columns(spec, ctx)
        assert result.errors[0].path.endswith("/field")


# ===========================================================================
# Semantic validation
# ===========================================================================


class TestSemanticValidation:
    def test_valid_encoding_passes(self, ctx):
        spec = {
            "encoding": {
                "x": {"field": "region", "type": "nominal"},
                "y": {"field": "revenue", "type": "quantitative"},
            }
        }
        result = validate_semantics(spec, ctx)
        assert result.ok

    def test_string_column_as_quantitative_fails(self, ctx):
        spec = {"encoding": {"x": {"field": "region", "type": "quantitative"}}}
        result = validate_semantics(spec, ctx)
        assert not result.ok
        assert result.stage_failed == "semantics"
        assert result.errors[0].code == "non_numeric_quantitative"

    def test_numeric_column_as_quantitative_passes(self, ctx):
        spec = {"encoding": {"y": {"field": "revenue", "type": "quantitative"}}}
        result = validate_semantics(spec, ctx)
        assert result.ok

    def test_numeric_aggregate_sum_passes(self, ctx):
        spec = {
            "encoding": {"y": {"field": "revenue", "aggregate": "sum", "type": "quantitative"}}
        }
        result = validate_semantics(spec, ctx)
        assert result.ok

    def test_string_column_aggregate_sum_fails(self, ctx):
        spec = {"encoding": {"x": {"field": "region", "aggregate": "sum"}}}
        result = validate_semantics(spec, ctx)
        assert not result.ok
        assert result.errors[0].code == "non_numeric_aggregate"

    def test_count_aggregate_on_string_passes(self, ctx):
        # count is allowed on any dtype
        spec = {"encoding": {"x": {"field": "region", "aggregate": "count"}}}
        result = validate_semantics(spec, ctx)
        assert result.ok

    def test_iso_date_strings_accepted_as_temporal(self, ctx):
        # ctx's "date" column has "2024-01-01" style values — should be temporal
        spec = {"encoding": {"x": {"field": "date", "type": "temporal"}}}
        result = validate_semantics(spec, ctx)
        assert result.ok

    def test_non_date_column_as_temporal_fails(self, ctx):
        spec = {"encoding": {"x": {"field": "region", "type": "temporal"}}}
        result = validate_semantics(spec, ctx)
        assert not result.ok
        assert result.errors[0].code == "non_temporal_temporal"

    def test_unknown_field_skipped(self, ctx):
        # columns validator catches missing fields; semantics should just ignore
        spec = {"encoding": {"x": {"field": "nonexistent", "type": "quantitative"}}}
        result = validate_semantics(spec, ctx)
        assert result.ok  # no col → no semantics error

    def test_no_field_key_skipped(self, ctx):
        # count without field is valid
        spec = {"encoding": {"x": {"aggregate": "count", "type": "quantitative"}}}
        result = validate_semantics(spec, ctx)
        assert result.ok


# ===========================================================================
# Data-ref validation
# ===========================================================================


class TestDataRefValidation:
    def test_correct_name_passes(self):
        result = validate_data_ref({"data": {"name": "table"}})
        assert result.ok

    def test_wrong_name_fails(self):
        result = validate_data_ref({"data": {"name": "sales"}})
        assert not result.ok
        assert result.stage_failed == "data_ref"
        assert result.errors[0].code == "wrong_data_name"

    def test_wrong_name_suggestion_mentions_table(self):
        result = validate_data_ref({"data": {"name": "sales"}})
        assert "table" in result.errors[0].suggestion

    def test_missing_data_key_fails(self):
        result = validate_data_ref({"mark": "bar"})
        assert not result.ok
        assert result.errors[0].code == "missing_data"

    def test_inline_values_fails(self):
        result = validate_data_ref({"data": {"values": [{"x": 1}]}})
        assert not result.ok
        assert result.errors[0].code == "inline_data"

    def test_url_data_fails(self):
        result = validate_data_ref({"data": {"url": "https://example.com/data.csv"}})
        assert not result.ok
        assert result.errors[0].code == "url_data"

    def test_custom_expected_name(self):
        result = validate_data_ref({"data": {"name": "my_table"}}, expected_name="my_table")
        assert result.ok

    def test_error_path_points_at_data(self):
        result = validate_data_ref({"mark": "bar"})
        assert result.errors[0].path == "/data"


# ===========================================================================
# Pipeline (run_validation) — short-circuit behaviour
# ===========================================================================


class TestValidationPipeline:
    def test_valid_spec_passes_all_stages(self, ctx, vega_lite_schema):
        result = run_validation(_VALID_SPEC, ctx, expected_data_name="table")
        assert result.ok

    def test_schema_failure_short_circuits(self, ctx):
        """When schema fails, columns/semantics validators must not run."""
        failed_schema = ValidationResult(
            ok=False,
            errors=[],
            stage_failed="schema",
        )
        with (
            patch("chart_llm.validation.pipeline.validate_schema", return_value=failed_schema),
            patch("chart_llm.validation.pipeline.validate_columns") as mock_cols,
            patch("chart_llm.validation.pipeline.validate_semantics") as mock_sem,
        ):
            result = run_validation({"mark": "bar"}, ctx)

        assert not result.ok
        assert result.stage_failed == "schema"
        mock_cols.assert_not_called()
        mock_sem.assert_not_called()

    def test_data_ref_failure_short_circuits_columns(self, ctx):
        ok = ValidationResult(ok=True, errors=[])
        failed_data_ref = ValidationResult(ok=False, errors=[], stage_failed="data_ref")
        with (
            patch("chart_llm.validation.pipeline.validate_schema", return_value=ok),
            patch("chart_llm.validation.pipeline.validate_data_ref", return_value=failed_data_ref),
            patch("chart_llm.validation.pipeline.validate_columns") as mock_cols,
        ):
            result = run_validation({"data": {"name": "sales"}}, ctx)

        assert result.stage_failed == "data_ref"
        mock_cols.assert_not_called()

    def test_wrong_data_name_caught_by_pipeline(self, ctx, vega_lite_schema):
        spec = {**_VALID_SPEC, "data": {"name": "sales"}}
        result = run_validation(spec, ctx, expected_data_name="table")
        assert not result.ok
        assert result.stage_failed == "data_ref"
        assert result.errors[0].code == "wrong_data_name"

    def test_column_error_caught_by_pipeline(self, ctx, vega_lite_schema):
        spec = {
            **_VALID_SPEC,
            "encoding": {
                "x": {"field": "regionn", "type": "nominal"},
                "y": {"field": "revenue", "type": "quantitative"},
            },
        }
        result = run_validation(spec, ctx, expected_data_name="table")
        assert not result.ok
        assert result.stage_failed == "columns"


class TestStructuralValidation:
    """Tests for validate_structural — common Vega-Lite structural mistakes."""

    from chart_llm.validation.structural import validate_structural

    _SCHEMA_URL = "https://vega.github.io/schema/vega-lite/v5.json"

    _BASE = {
        "$schema": _SCHEMA_URL,
        "data": {"name": "table"},
        "mark": "bar",
        "encoding": {
            "x": {"field": "region", "type": "nominal"},
            "y": {"field": "revenue", "type": "quantitative", "aggregate": "sum"},
        },
    }

    def test_valid_spec_passes(self):
        from chart_llm.validation.structural import validate_structural
        result = validate_structural(self._BASE)
        assert result.ok is True
        assert result.errors == []

    def test_facet_in_encoding_fails(self):
        from chart_llm.validation.structural import validate_structural
        spec = {
            **self._BASE,
            "encoding": {**self._BASE["encoding"], "facet": {"field": "region", "type": "nominal"}},
        }
        result = validate_structural(spec)
        assert result.ok is False
        assert result.stage_failed == "structural"
        codes = [e.code for e in result.errors]
        assert "facet_in_encoding" in codes

    def test_row_in_encoding_fails(self):
        from chart_llm.validation.structural import validate_structural
        spec = {
            **self._BASE,
            "encoding": {**self._BASE["encoding"], "row": {"field": "product", "type": "nominal"}},
        }
        result = validate_structural(spec)
        assert result.ok is False
        assert any(e.code == "row_in_encoding" for e in result.errors)

    def test_column_in_encoding_fails(self):
        from chart_llm.validation.structural import validate_structural
        spec = {
            **self._BASE,
            "encoding": {**self._BASE["encoding"], "column": {"field": "product", "type": "nominal"}},
        }
        result = validate_structural(spec)
        assert result.ok is False
        assert any(e.code == "column_in_encoding" for e in result.errors)

    def test_filter_at_top_level_fails(self):
        from chart_llm.validation.structural import validate_structural
        spec = {**self._BASE, "filter": "datum.region === 'West'"}
        result = validate_structural(spec)
        assert result.ok is False
        assert any(e.code == "filter_at_top_level" for e in result.errors)

    def test_filter_in_encoding_fails(self):
        from chart_llm.validation.structural import validate_structural
        spec = {
            **self._BASE,
            "encoding": {
                **self._BASE["encoding"],
                "filter": {"field": "region", "equal": "West"},
            },
        }
        result = validate_structural(spec)
        assert result.ok is False
        assert any(e.code == "filter_in_encoding" for e in result.errors)

    def test_aggregate_at_top_level_fails(self):
        from chart_llm.validation.structural import validate_structural
        spec = {**self._BASE, "aggregate": [{"op": "sum", "field": "revenue", "as": "total"}]}
        result = validate_structural(spec)
        assert result.ok is False
        assert any(e.code == "aggregate_at_top_level" for e in result.errors)

    def test_calculate_at_top_level_fails(self):
        from chart_llm.validation.structural import validate_structural
        spec = {**self._BASE, "calculate": "datum.revenue * 2"}
        result = validate_structural(spec)
        assert result.ok is False
        assert any(e.code == "calculate_at_top_level" for e in result.errors)

    def test_transform_not_a_list_fails(self):
        from chart_llm.validation.structural import validate_structural
        spec = {**self._BASE, "transform": {"filter": "datum.region === 'West'"}}
        result = validate_structural(spec)
        assert result.ok is False
        assert any(e.code == "transform_not_a_list" for e in result.errors)

    def test_transform_as_list_passes(self):
        from chart_llm.validation.structural import validate_structural
        spec = {**self._BASE, "transform": [{"filter": "datum.region === 'West'"}]}
        result = validate_structural(spec)
        assert result.ok is True

    def test_structural_errors_have_suggestions(self):
        from chart_llm.validation.structural import validate_structural
        spec = {
            **self._BASE,
            "encoding": {**self._BASE["encoding"], "facet": {"field": "region", "type": "nominal"}},
        }
        result = validate_structural(spec)
        assert all(e.suggestion is not None for e in result.errors)

    def test_structural_runs_before_data_ref_in_pipeline(self, ctx, vega_lite_schema):
        """Structural check must short-circuit before data_ref so we get structural errors."""
        from chart_llm.pipeline.dataset import DatasetContext
        from chart_llm.validation.pipeline import run_validation
        spec = {
            **self._BASE,
            "data": {"name": "wrong"},
            "encoding": {**self._BASE["encoding"], "facet": {"field": "region", "type": "nominal"}},
        }
        result = run_validation(spec, ctx, expected_data_name="table")
        assert result.stage_failed == "structural"


class TestRenderValidation:
    """Tests for validate_render — the optional render stage."""

    _SCHEMA_URL = "https://vega.github.io/schema/vega-lite/v5.json"

    _BASE = {
        "$schema": _SCHEMA_URL,
        "data": {"name": "table"},
        "mark": "bar",
        "encoding": {
            "x": {"field": "region", "type": "nominal"},
            "y": {"field": "revenue", "type": "quantitative", "aggregate": "sum"},
        },
    }

    def test_valid_spec_renders_ok(self, ctx, vega_lite_schema):
        """A valid spec + real df should produce ok=True."""
        from chart_llm.validation.render import validate_render
        result = validate_render(self._BASE, ctx)
        assert result.ok is True
        assert result.errors == []

    def test_render_error_produces_render_failed(self, ctx, vega_lite_schema):
        """If render_to_html raises RenderError, stage_failed='render' and code='render_failed'."""
        from unittest.mock import patch

        from chart_llm.rendering.render import RenderError
        from chart_llm.validation.render import validate_render

        with patch("chart_llm.validation.render.render_to_html", side_effect=RenderError("vl-convert exploded")):
            result = validate_render(self._BASE, ctx)

        assert result.ok is False
        assert result.stage_failed == "render"
        assert result.errors[0].code == "render_failed"
        assert "vl-convert exploded" in result.errors[0].message

    def test_bad_column_spec_stopped_before_render(self, ctx, vega_lite_schema):
        """Columns validator must short-circuit before render — bad-column spec never reaches render stage."""
        from unittest.mock import patch

        from chart_llm.validation.pipeline import run_validation

        bad_col_spec = {
            **self._BASE,
            "encoding": {
                "x": {"field": "nonexistent_col", "type": "nominal"},
                "y": {"field": "revenue", "type": "quantitative", "aggregate": "sum"},
            },
        }
        with patch("chart_llm.validation.render.render_to_html") as mock_render:
            result = run_validation(bad_col_spec, ctx, include_render=True)

        mock_render.assert_not_called()
        assert result.stage_failed == "columns"

    def test_include_render_false_skips_render_stage(self, ctx, vega_lite_schema):
        """When include_render=False (default), render_to_html is never called."""
        from unittest.mock import patch

        from chart_llm.validation.pipeline import run_validation

        with patch("chart_llm.validation.render.render_to_html") as mock_render:
            result = run_validation(self._BASE, ctx, include_render=False)

        mock_render.assert_not_called()
        assert result.ok is True

    def test_include_render_true_calls_render_stage(self, ctx, vega_lite_schema):
        """When include_render=True, render_to_html is called on a passing spec."""
        from unittest.mock import patch

        from chart_llm.validation.pipeline import run_validation

        with patch("chart_llm.validation.render.render_to_html", return_value="<html/>") as mock_render:
            result = run_validation(self._BASE, ctx, include_render=True)

        mock_render.assert_called_once()
        assert result.ok is True

    def test_unexpected_exception_becomes_render_failed(self, ctx, vega_lite_schema):
        """Non-RenderError exceptions from render_to_html are also caught and reported."""
        from unittest.mock import patch

        from chart_llm.validation.render import validate_render

        with patch("chart_llm.validation.render.render_to_html", side_effect=ValueError("unexpected")):
            result = validate_render(self._BASE, ctx)

        assert result.ok is False
        assert result.stage_failed == "render"
        assert result.errors[0].code == "render_failed"
