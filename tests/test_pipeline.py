"""Tests for the generation pipeline and retry logic."""

import pytest

# TODO: mock LLMModel to return canned responses
# TODO: test run_pipeline succeeds on first attempt when spec is valid
# TODO: test retry loop triggers on invalid spec and succeeds on second attempt
# TODO: test retry loop raises ValueError after max_retries exhausted
# TODO: test validate=False skips validation and returns whatever the model returns
