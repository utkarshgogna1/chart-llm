"""Load and cache prompt text files."""

from functools import lru_cache
from pathlib import Path

_DIR = Path(__file__).parent


@lru_cache(maxsize=1)
def load_prompts() -> tuple[str, str]:
    """Return (system_prompt, user_template). Reads files once, then cached."""
    system = (_DIR / "system.txt").read_text()
    user_template = (_DIR / "user_template.txt").read_text()
    return system, user_template


@lru_cache(maxsize=1)
def load_feedback_template() -> str:
    """Return the retry feedback template. Reads file once, then cached."""
    return (_DIR / "feedback_template.txt").read_text()
