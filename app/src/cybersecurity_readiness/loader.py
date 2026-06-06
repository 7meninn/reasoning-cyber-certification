from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .schemas import LearnerProfile, ScenarioLab


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = PROJECT_ROOT / "data" / "synthetic"
DEFAULT_LAB_ID = "LAB-SOC-001"


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


def load_labs() -> list[ScenarioLab]:
    lab_dir = DATA_DIR / "labs"
    labs: list[ScenarioLab] = []
    for path in sorted(lab_dir.glob("*.json")):
        with path.open("r", encoding="utf-8") as handle:
            labs.append(ScenarioLab.model_validate(json.load(handle)))
    labs.sort(key=lambda lab: (lab.lab_id != DEFAULT_LAB_ID, lab.lab_id))
    return labs


def get_lab(lab_id: str | None = None) -> ScenarioLab:
    target_lab_id = lab_id or DEFAULT_LAB_ID
    for lab in load_labs():
        if lab.lab_id == target_lab_id:
            return lab
    raise ValueError(f"Unknown lab_id: {target_lab_id}")
