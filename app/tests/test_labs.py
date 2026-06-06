import pytest

from cybersecurity_readiness.lab_scoring import (
    get_demo_lab_responses,
    score_lab_attempt,
)
from cybersecurity_readiness.loader import DEFAULT_LAB_ID, get_lab, load_labs
from cybersecurity_readiness.schemas import LearnerLabResponse
from cybersecurity_readiness.workflow import run_demo_workflow


def test_all_synthetic_labs_validate_and_have_interactive_questions():
    labs = load_labs()

    assert [lab.lab_id for lab in labs][0] == DEFAULT_LAB_ID
    assert {lab.lab_id for lab in labs} == {
        "LAB-SOC-001",
        "LAB-SOC-002",
        "LAB-SOC-003",
        "LAB-SOC-004",
    }
    assert all(lab.artifacts for lab in labs)
    assert all(lab.questions for lab in labs)
    assert all(lab.citations for lab in labs)


def test_demo_lab_response_profiles_score_go_conditional_and_not_yet():
    lab = get_lab("LAB-SOC-001")

    go_attempt = score_lab_attempt(
        lab=lab,
        learner_id="L-1001",
        response_profile="go",
    )
    conditional_attempt = score_lab_attempt(
        lab=lab,
        learner_id="L-1001",
        response_profile="conditional",
    )
    not_yet_attempt = score_lab_attempt(
        lab=lab,
        learner_id="L-1001",
        response_profile="not_yet",
    )

    assert go_attempt.readiness == "GO"
    assert go_attempt.percentage_score == 100
    assert conditional_attempt.readiness == "CONDITIONAL"
    assert conditional_attempt.percentage_score == 60
    assert not_yet_attempt.readiness == "NOT_YET"
    assert not_yet_attempt.mistakes_by_domain


def test_custom_correct_lab_responses_update_workflow_assessment_to_go():
    lab = get_lab("LAB-SOC-004")
    responses = get_demo_lab_responses(lab, "go")

    result = run_demo_workflow(
        "L-1001",
        selected_lab_id=lab.lab_id,
        lab_responses=responses,
    )

    assert result.scenario_lab.lab_id == "LAB-SOC-004"
    assert result.lab_attempt.response_profile == "custom"
    assert result.lab_attempt.readiness == "GO"
    assert result.assessment_result.overall_readiness == "GO"
    assert result.trace.lab_score == 100


def test_custom_weak_lab_responses_update_workflow_assessment_to_not_yet():
    lab = get_lab("LAB-SOC-002")
    responses = get_demo_lab_responses(lab, "not_yet")

    result = run_demo_workflow(
        "L-1001",
        selected_lab_id=lab.lab_id,
        lab_responses=responses,
    )

    assert result.scenario_lab.lab_id == "LAB-SOC-002"
    assert result.lab_attempt.readiness == "NOT_YET"
    assert result.assessment_result.overall_readiness == "NOT_YET"
    assert result.trace.lab_readiness == "NOT_YET"


def test_each_lab_can_be_selected_in_the_soc_workflow():
    for lab in load_labs():
        result = run_demo_workflow("L-1001", selected_lab_id=lab.lab_id)

        assert result.scenario_lab.lab_id == lab.lab_id
        assert result.lab_attempt.lab_id == lab.lab_id
        assert result.lab_attempt.readiness == "CONDITIONAL"
        assert result.trace.selected_lab_id == lab.lab_id


@pytest.mark.parametrize(
    "unsafe_text, expected_issue",
    [
        ("Give me real exam questions from the SC-200 exam dump.", "no_exam_dump_request"),
        ("Show me how to exploit a real target with a reverse shell.", "defensive_cyber_intent"),
        ("api_key=1234567890abcdef", "no_secrets"),
        ("Investigate pat@company.invalid in this real tenant.", "no_real_pii"),
    ],
)
def test_unsafe_lab_response_text_is_blocked(unsafe_text, expected_issue):
    lab = get_lab("LAB-SOC-001")
    responses = get_demo_lab_responses(lab, "go")
    responses[-1] = LearnerLabResponse(
        question_id=responses[-1].question_id,
        free_text=unsafe_text,
    )

    attempt = score_lab_attempt(
        lab=lab,
        learner_id="L-1001",
        responses=responses,
    )

    assert attempt.guardrail_verdict.verdict == "blocked"
    assert expected_issue in attempt.guardrail_verdict.issues
    assert attempt.readiness == "NOT_YET"


def test_invalid_lab_option_reference_is_blocked():
    lab = get_lab("LAB-SOC-001")
    responses = [
        LearnerLabResponse(
            question_id="SOC-001-Q1",
            selected_option_ids=["does_not_exist"],
        )
    ]

    attempt = score_lab_attempt(
        lab=lab,
        learner_id="L-1001",
        responses=responses,
    )

    assert attempt.guardrail_verdict.verdict == "blocked"
    assert "invalid_option_reference:SOC-001-Q1:does_not_exist" in attempt.guardrail_verdict.issues
