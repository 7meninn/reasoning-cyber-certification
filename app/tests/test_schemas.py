import pytest
from pydantic import ValidationError

from cybersecurity_readiness.schemas import (
    Citation,
    GuardrailVerdict,
    LabAttempt,
    LabOption,
    LabQuestion,
    LabScoreBreakdown,
    LearnerLabResponse,
    LearnerProfile,
    RouteDecision,
)


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


def test_lab_question_rejects_unknown_expected_option_reference():
    with pytest.raises(ValidationError, match="unknown options"):
        LabQuestion.model_validate(
            {
                "question_id": "Q1",
                "prompt": "Pick one.",
                "response_type": "single_choice",
                "domain": "Alert triage",
                "points": 4,
                "options": [
                    {"option_id": "known", "label": "Known", "text": "Known option"}
                ],
                "expected_option_ids": ["missing"],
                "expected_keywords": [],
                "explanation": "Missing option should fail.",
                "citations": [],
            }
        )


def test_learner_lab_response_rejects_duplicate_selected_options():
    with pytest.raises(ValidationError, match="duplicates"):
        LearnerLabResponse(
            question_id="Q1",
            selected_option_ids=["a", "a"],
        )


def test_lab_score_breakdown_rejects_earned_points_above_max():
    with pytest.raises(ValidationError, match="earned_points"):
        LabScoreBreakdown(
            question_id="Q1",
            domain="Alert triage",
            criterion="Score shape",
            earned_points=5,
            max_points=4,
            feedback="Invalid",
        )


def test_lab_attempt_rejects_out_of_range_domain_scores():
    citation = Citation(
        source_id="SYN-TEST",
        title="Synthetic test source",
        source_type="synthetic_internal",
        excerpt="Synthetic source for schema tests.",
    )
    with pytest.raises(ValidationError, match="score must be between 0 and 100"):
        LabAttempt(
            lab_id="LAB-TEST",
            learner_id="L-TEST",
            response_profile="custom",
            responses=[LearnerLabResponse(question_id="Q1")],
            score_breakdown=[
                LabScoreBreakdown(
                    question_id="Q1",
                    domain="Alert triage",
                    criterion="Schema",
                    earned_points=1,
                    max_points=1,
                    feedback="Valid",
                )
            ],
            total_score=1,
            max_score=1,
            percentage_score=100,
            readiness="GO",
            domain_scores={"Alert triage": 101},
            mistakes_by_domain={},
            remediation_focus=[],
            adaptive_remediation_reason="No remediation needed.",
            guardrail_verdict=GuardrailVerdict(
                verdict="allowed",
                issues=[],
                checks={"safe": True},
            ),
            citations=[citation],
            confidence=0.9,
        )


def test_lab_option_schema_accepts_minimal_valid_option():
    option = LabOption(option_id="triage", label="Triage", text="Start triage.")

    assert option.option_id == "triage"
