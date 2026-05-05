"""Prompt builders for Vega-Lite generation and retry-with-feedback."""

# TODO: tune system prompt with Vega-Lite schema summary and few-shot examples

SYSTEM_PROMPT = """\
You are an expert data visualization assistant. Given a CSV schema and a natural-language question,
output a valid Vega-Lite v5 JSON specification that answers the question.
Return ONLY valid JSON — no markdown, no explanation.
"""


def build_generation_prompt(csv_schema: str, question: str) -> str:
    """Build the user turn for the initial spec generation request."""
    # TODO: include field names, dtypes, and sample rows from csv_schema
    return f"CSV schema:\n{csv_schema}\n\nQuestion: {question}"


def build_retry_prompt(
    csv_schema: str,
    question: str,
    previous_spec: str,
    validation_errors: list[str],
) -> str:
    """Build the user turn for a retry after validation failure."""
    # TODO: format errors clearly so the model can pinpoint the problem
    errors_block = "\n".join(f"- {e}" for e in validation_errors)
    return (
        f"CSV schema:\n{csv_schema}\n\n"
        f"Question: {question}\n\n"
        f"Your previous Vega-Lite spec had these errors:\n{errors_block}\n\n"
        f"Previous spec:\n{previous_spec}\n\n"
        "Please fix the spec and return valid JSON only."
    )
