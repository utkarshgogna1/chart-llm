"""Tests for dataset context and generate_spec pipeline step."""

import json
from pathlib import Path

import pandas as pd
import pytest

from chart_llm.models.base import LLMModel, LLMResponse
from chart_llm.pipeline.dataset import DatasetContext, build_dataset_context
from chart_llm.pipeline.generate import GenerationResult, generate_spec

SALES_CSV = Path(__file__).parent.parent / "benchmarks" / "datasets" / "sales.csv"

_FAKE_SPEC = {
    "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
    "data": {"name": "table"},
    "mark": "bar",
    "encoding": {
        "x": {"field": "region", "type": "nominal"},
        "y": {"field": "revenue", "aggregate": "sum", "type": "quantitative"},
    },
    "title": "Revenue by region",
}


class FakeClient(LLMModel):
    def generate(self, system: str, user: str, max_retries: int = 2) -> LLMResponse:
        return LLMResponse(
            text=json.dumps(_FAKE_SPEC),
            model_name="fake-model",
            latency_ms=42.0,
            prompt_tokens=100,
            completion_tokens=50,
        )


class CapturingClient(LLMModel):
    def __init__(self):
        self.last_system = ""
        self.last_user = ""

    def generate(self, system: str, user: str, max_retries: int = 2) -> LLMResponse:
        self.last_system = system
        self.last_user = user
        return LLMResponse(
            text=json.dumps(_FAKE_SPEC),
            model_name="capturing",
            latency_ms=1.0,
        )


# ===========================================================================
# DatasetContext
# ===========================================================================


class TestDatasetContext:
    def test_column_names_match_csv(self):
        ctx = build_dataset_context(SALES_CSV)
        assert [c.name for c in ctx.column_schema] == [
            "date", "region", "product", "units", "revenue"
        ]

    def test_row_count_and_name(self):
        ctx = build_dataset_context(SALES_CSV)
        assert ctx.row_count == 50
        assert ctx.name == "sales"

    def test_region_column_info(self):
        ctx = build_dataset_context(SALES_CSV)
        region = next(c for c in ctx.column_schema if c.name == "region")
        assert region.n_unique == 4
        assert region.n_null == 0
        assert len(region.sample_values) <= 3
        assert all(v in ("North", "South", "East", "West") for v in region.sample_values)

    def test_sample_values_are_strings(self):
        ctx = build_dataset_context(SALES_CSV)
        for col in ctx.column_schema:
            assert all(isinstance(v, str) for v in col.sample_values)

    def test_df_attached_as_dataframe(self):
        ctx = build_dataset_context(SALES_CSV)
        assert isinstance(ctx.df, pd.DataFrame)
        assert len(ctx.df) == 50

    def test_df_excluded_from_model_dump(self):
        ctx = build_dataset_context(SALES_CSV)
        dumped = ctx.model_dump()
        assert "df" not in dumped
        assert "column_schema" in dumped
        assert "row_count" in dumped


# ===========================================================================
# generate_spec
# ===========================================================================


class TestGenerateSpec:
    def test_returns_generation_result(self):
        ctx = build_dataset_context(SALES_CSV)
        result = generate_spec(FakeClient(), ctx, "Show revenue by region")
        assert isinstance(result, GenerationResult)

    def test_spec_parsed_correctly(self):
        ctx = build_dataset_context(SALES_CSV)
        result = generate_spec(FakeClient(), ctx, "Show revenue by region")
        assert result.spec == _FAKE_SPEC
        assert result.spec["mark"] == "bar"

    def test_metadata_populated(self):
        ctx = build_dataset_context(SALES_CSV)
        result = generate_spec(FakeClient(), ctx, "Show revenue by region")
        assert result.model_name == "fake-model"
        assert result.latency_ms == 42.0
        assert result.prompt_tokens == 100
        assert result.completion_tokens == 50

    def test_raw_text_is_valid_json_of_spec(self):
        ctx = build_dataset_context(SALES_CSV)
        result = generate_spec(FakeClient(), ctx, "Show revenue by region")
        assert json.loads(result.raw_text) == _FAKE_SPEC

    def test_user_prompt_contains_column_names(self):
        ctx = build_dataset_context(SALES_CSV)
        client = CapturingClient()
        generate_spec(client, ctx, "Total revenue per region")

        assert "region" in client.last_user
        assert "revenue" in client.last_user
        assert "date" in client.last_user
        assert "Total revenue per region" in client.last_user

    def test_system_prompt_loaded(self):
        ctx = build_dataset_context(SALES_CSV)
        client = CapturingClient()
        generate_spec(client, ctx, "anything")

        assert "Vega-Lite" in client.last_system
        assert "JSON" in client.last_system
