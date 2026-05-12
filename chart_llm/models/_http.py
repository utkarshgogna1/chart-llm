"""Shared HTTP retry helper for LLM adapters."""

import time
from typing import Optional

import httpx

_DEFAULT_BACKOFF_DELAYS = [2, 4, 8]


def post_with_backoff(
    client: httpx.Client,
    url: str,
    max_retries: int,
    *,
    retry_delays: Optional[list[int]] = None,
    **kwargs,
) -> tuple[httpx.Response, float]:
    """POST url, retrying on 429 with exponential backoff.

    Returns (response, latency_ms). Raises the last HTTPStatusError after
    max_retries are exhausted, or raises immediately on any non-429 error.

    retry_delays: custom delay schedule (seconds). Defaults to _DEFAULT_BACKOFF_DELAYS.
    """
    delays = retry_delays if retry_delays is not None else _DEFAULT_BACKOFF_DELAYS
    last_exc: Exception | None = None
    for attempt in range(max_retries + 1):
        if attempt > 0:
            delay = delays[min(attempt - 1, len(delays) - 1)]
            time.sleep(delay)

        t0 = time.perf_counter()
        resp = client.post(url, **kwargs)
        latency_ms = (time.perf_counter() - t0) * 1000

        if resp.status_code == 429:
            last_exc = httpx.HTTPStatusError(
                f"Rate limited (429) on attempt {attempt + 1}",
                request=resp.request,
                response=resp,
            )
            continue

        resp.raise_for_status()
        return resp, latency_ms

    raise last_exc  # type: ignore[misc]
