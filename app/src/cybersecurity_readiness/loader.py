from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .schemas import LearnerProfile


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = PROJECT_ROOT / "data" / "synthetic"


def load_json(relative_path: str) -> Any:
    path = DATA_DIR / relative_path
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_learners() -> list[LearnerProfile]:
    rows = load_json("learners.json")
    return [LearnerProfile.model_validate(row) for row in rows]


def get_learner(learner_id: str) -> LearnerProfile:
    for learner in load_learners():
        if learner.learner_id == learner_id:
            return learner
    raise ValueError(f"Unknown learner_id: {learner_id}")

