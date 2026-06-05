import pytest
from pydantic import ValidationError

from cybersecurity_readiness.schemas import LearnerProfile, RouteDecision


def test_learner_profile_rejects_out_of_range_skill_scores():
    with pytest.raises(ValidationError):
        LearnerProfile.model_validate(
            {
                "learner_id": "L-TEST",
                "employee_id": "EMP-TEST",
                "role_current": "Helpdesk Analyst",
                "role_target": "SOC Analyst",
                "experience_level": "Entry",
                "completed_certifications": [],
                "preferred_learning_style": "Scenario-first",
                "available_focus_hours_per_week": 6,
                "constraints": [],
                "skills_self_rating": {"kql": 6},
            }
        )


def test_schemas_forbid_extra_fields():
    with pytest.raises(ValidationError):
        RouteDecision.model_validate(
            {
                "route": "soc_readiness_demo",
                "learner_id": "L-1001",
                "goal": "SOC readiness",
                "risk_flags": [],
                "next_agents": [],
                "confidence": 0.9,
                "unexpected": "should fail",
            }
        )

