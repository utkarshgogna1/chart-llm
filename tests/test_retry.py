"""Tests for the generate_validated_spec retry loop."""

import json

import pandas as pd
import pytest

from chart_llm.models.base import LLMModel, LLMResponse
from chart_llm.pipeline.dataset import ColumnInfo, DatasetContext
from chart_llm.pipeline.retry import ValidatedRun, generate_validated_spec

# ---------------------------------------------------------------------------
# Shared fixtures
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

_WRONG_DATA_SPEC = {
    "$schema": _SCHEMA_URL,
    "data": {"name": "sales"},  # wrong — should be "table"
    "mark": "bar",
    "encoding": {
        "x": {"field": "region", "type": "nominal"},
        "y": {"field": "revenue", "aggregate": "sum", "type": "quantitative"},
    },
    "title": "Revenue by region",
}

_BAD_COLUMN_SPEC = {
    "$schema": _SCHEMA_URL,
    "data": {"name": "table"},
    "mark": "bar",
    "encoding": {
        "x": {"field": "hallucinated_col", "type": "nominal"},
        "y": {"field": "revenue", "aggregate": "sum", "type": "quantitative"},
    },
    "title": "Bad spec",
}


@pytest.fixture
def ctx() -> DatasetContext:
    """Tiny in-memory DatasetContext — no CSV loading, no network."""
    df = pd.DataFrame(
        {
            "region": ["North", "South", "East"],
            "revenue": [1000.0, 2000.0, 3000.0],
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
        ],
        row_count=3,
    )


class FakeSequenceClient(LLMModel):
    """Returns canned LLMResponse texts in sequence; records every (system, user) call."""

    def __init__(
        self, texts: list[str], *, prompt_tokens: int = 50, completion_tokens: int = 30
    ):
        self._texts = texts
        self._idx = 0
        self._pt = prompt_tokens
        self._ct = completion_tokens
        self.calls: list[tuple[str, str]] = []  # (system, user) per call

    def generate(self, system: str, user: str, max_retries: int = 2) -> LLMResponse:
        self.calls.append((system, user))
        text = self._texts[self._idx]
        self._idx += 1
        return LLMResponse(
            text=text,
            model_name="fake",
            latency_ms=10.0,
            prompt_tokens=self._pt,
            completion_tokens=self._ct,
        )


# ---------------------------------------------------------------------------
# Test 1: first response already valid → 1 attempt, succeeded
# ---------------------------------------------------------------------------


def test_succeeds_on_first_attempt(ctx, vega_lite_schema):
    client = FakeSequenceClient([json.dumps(_VALID_SPEC)])
    run = generate_validated_spec(client, ctx, "Show revenue by region", max_attempts=3)

    assert isinstance(run, ValidatedRun)
    assert run.succeeded is True
    assert run.stop_reason == "validated"
    assert len(run.attempts) == 1
    assert run.attempts[0].attempt_number == 1
    assert run.attempts[0].validation.ok is True
    assert run.final_spec == _VALID_SPEC


# ---------------------------------------------------------------------------
# Test 2: first fails (wrong data name), second succeeds → 2 attempts
# ---------------------------------------------------------------------------


def test_retry_succeeds_on_second_attempt(ctx, vega_lite_schema):
    client = FakeSequenceClient(
        [
            json.dumps(_WRONG_DATA_SPEC),
            json.dumps(_VALID_SPEC),
        ]
    )
    run = generate_validated_spec(client, ctx, "Show revenue by region", max_attempts=3)

    assert run.succeeded is True
    assert run.stop_reason == "validated"
    assert len(run.attempts) == 2
    assert run.attempts[0].validation.ok is False
    assert run.attempts[0].validation.stage_failed == "data_ref"
    assert run.attempts[1].validation.ok is True
    assert run.final_spec == _VALID_SPEC


# ---------------------------------------------------------------------------
# Test 3: every response has a hallucinated column → max_attempts exhausted
# ---------------------------------------------------------------------------


def test_max_attempts_exhausted(ctx, vega_lite_schema):
    client = FakeSequenceClient([json.dumps(_BAD_COLUMN_SPEC)] * 3)
    run = generate_validated_spec(client, ctx, "Show revenue", max_attempts=3)

    assert run.succeeded is False
    assert run.stop_reason == "max_attempts"
    assert len(run.attempts) == 3
    assert all(not a.validation.ok for a in run.attempts)
    assert run.final_spec is None


# ---------------------------------------------------------------------------
# Test 4: first response is unparseable JSON → invalid_json recorded, retry continues
# ---------------------------------------------------------------------------


def test_invalid_json_recorded_and_retry_continues(ctx, vega_lite_schema):
    garbage = "here is your chart: sorry I forgot the JSON"
    client = FakeSequenceClient([garbage, json.dumps(_VALID_SPEC)])
    run = generate_validated_spec(client, ctx, "Show revenue", max_attempts=3)

    assert len(run.attempts) == 2
    first = run.attempts[0]
    assert first.spec is None
    assert first.validation.ok is False
    assert first.validation.errors[0].code == "invalid_json"
    assert first.raw_text == garbage
    # Second attempt succeeds
    assert run.succeeded is True


# ---------------------------------------------------------------------------
# Test 5: feedback prompt for attempt 2 contains the validation errors
# ---------------------------------------------------------------------------


def test_retry_prompt_contains_validation_errors(ctx, vega_lite_schema):
    client = FakeSequenceClient(
        [
            json.dumps(_WRONG_DATA_SPEC),
            json.dumps(_VALID_SPEC),
        ]
    )
    generate_validated_spec(client, ctx, "Show revenue by region", max_attempts=3)

    assert len(client.calls) == 2
    _, user_prompt_attempt2 = client.calls[1]

    # The feedback prompt should echo the original question
    assert "Show revenue by region" in user_prompt_attempt2
    # And surface the validation error from attempt 1
    assert "wrong_data_name" in user_prompt_attempt2
    # And include the previous (broken) spec
    assert "sales" in user_prompt_attempt2


def test_retry_prompt_contains_invalid_json_error(ctx, vega_lite_schema):
    garbage = "NOT JSON AT ALL"
    client = FakeSequenceClient([garbage, json.dumps(_VALID_SPEC)])
    generate_validated_spec(client, ctx, "Any question", max_attempts=3)

    _, user_prompt_attempt2 = client.calls[1]
    assert "invalid_json" in user_prompt_attempt2
    assert garbage in user_prompt_attempt2


# ---------------------------------------------------------------------------
# Test 6: total_tokens correctly sums across attempts
# ---------------------------------------------------------------------------


def test_total_tokens_summed_across_attempts(ctx, vega_lite_schema):
    client = FakeSequenceClient(
        [json.dumps(_WRONG_DATA_SPEC), json.dumps(_VALID_SPEC)],
        prompt_tokens=100,
        completion_tokens=40,
    )
    run = generate_validated_spec(client, ctx, "Show revenue", max_attempts=3)

    assert run.total_tokens.prompt == 200  # 100 × 2 attempts
    assert run.total_tokens.completion == 80  # 40 × 2 attempts
    assert run.total_tokens.total == 280  # 200 + 80


def test_total_latency_summed_across_attempts(ctx, vega_lite_schema):
    client = FakeSequenceClient(
        [json.dumps(_WRONG_DATA_SPEC), json.dumps(_VALID_SPEC)],
    )
    run = generate_validated_spec(client, ctx, "Show revenue", max_attempts=3)
    # Each FakeSequenceClient call has latency_ms=10.0; 2 calls → 20.0
    assert run.total_latency_ms == pytest.approx(20.0)


# ---------------------------------------------------------------------------
# stop_reason="generation_error" when client raises
# ---------------------------------------------------------------------------


def test_generation_error_stop_reason(ctx):
    class FailingClient(LLMModel):
        def generate(self, system, user, max_retries=2):
            raise RuntimeError("network down")

    run = generate_validated_spec(FailingClient(), ctx, "Show revenue", max_attempts=3)

    assert run.succeeded is False
    assert run.stop_reason == "generation_error"
    assert run.attempts == []


def test_http_status_error_stops_loop_immediately(ctx):
    import httpx

    class RateLimitedClient(LLMModel):
        def generate(self, system, user, max_retries=2):
            req = httpx.Request("POST", "http://fake.api")
            raise httpx.HTTPStatusError(
                "Rate limited (429)",
                request=req,
                response=httpx.Response(429),
            )

    run = generate_validated_spec(
        RateLimitedClient(), ctx, "Show revenue", max_attempts=3
    )

    assert run.succeeded is False
    assert run.stop_reason == "generation_error"
    assert run.error is not None
    assert "429" in run.error
    assert len(run.attempts) == 0  # stopped before any attempt was recorded
