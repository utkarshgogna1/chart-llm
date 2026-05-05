"""Shared HTTP retry helper for LLM adapters."""

import time

import httpx

_BACKOFF_DELAYS = [2, 4, 8]


def post_with_backoff(
    client: httpx.Client,
    url: str,
    max_retries: int,
    **kwargs,
) -> tuple[httpx.Response, float]:
    """POST url, retrying on 429 with exponential backoff.

    Returns (response, latency_ms). Raises the last HTTPStatusError after
    max_retries are exhausted, or raises immediately on any non-429 error.
    """
    last_exc: Exception | None = None
    for attempt in range(max_retries + 1):
        if attempt > 0:
            delay = _BACKOFF_DELAYS[min(attempt - 1, len(_BACKOFF_DELAYS) - 1)]
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
