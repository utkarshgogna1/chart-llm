"""Load benchmark queries from JSON files."""

import json
from pathlib import Path
from typing import Literal, Optional

from pydantic import BaseModel


class BenchmarkQuery(BaseModel):
    id: str
    dataset: str
    question: str
    ground_truth_spec: Optional[dict] = None
    tags: list[str]
    difficulty: Literal["easy", "medium", "hard"]
    expects_no_correct_answer: bool = False


def load_benchmark(directory: Path) -> list[BenchmarkQuery]:
    """Return BenchmarkQuery objects for every *.json file in directory, sorted by filename."""
    queries = []
    for path in sorted(directory.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        queries.append(BenchmarkQuery(**data))
    return queries
