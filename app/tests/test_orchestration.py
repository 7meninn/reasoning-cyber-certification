from typing import Any

from cybersecurity_readiness.agents import MockIntakeRouterAgent
from cybersecurity_readiness.loader import get_learner
from cybersecurity_readiness.orchestration.executor import AgentExecutor
from cybersecurity_readiness.orchestration.state import WorkflowState
from cybersecurity_readiness.schemas import RouteDecision, RunTrace
from cybersecurity_readiness.workflow import run_demo_workflow


class InvalidRouteAgent:
    name = "Invalid Route Agent"
    output_schema = RouteDecision
    latency_ms = 7

    def raw_response(self, context: Any | None = None) -> str:
        return '{"route": "soc_readiness_demo"}'


def make_state() -> WorkflowState:
    return WorkflowState(
        request_text="test",
        learner=get_learner("L-1001"),
        trace=RunTrace(run_id="TEST-ORCH", route="pending"),
    )


def test_soc_route_executes_expected_agents_in_order():
    result = run_demo_workflow("L-1001")

    assert [step.agent_name for step in result.trace.agent_steps] == [
        "Intake Router Agent",
        "Knowledge Curator Agent",
        "Certification Path Advisor Agent",
        "Skill Gap Analyst Agent",
        "Study Plan Generator Agent",
        "Scenario Lab Coach Agent",
        "Assessment Agent",
        "Manager Insights Agent",
        "Verifier and Safety Agent",
    ]
    assert all(step.status == "success" for step in result.trace.agent_steps)


def test_manager_route_skips_learner_only_steps():
    result = run_demo_workflow(
        "L-1001",
        "Show the manager dashboard with team readiness and capacity risk.",
    )

    assert result.route.route == "manager_insights"
    assert result.manager_insight is not None
    assert result.certification_path is None
    assert result.skill_gap_report is None
    assert result.study_plan is None
    assert result.scenario_lab is None
    assert result.assessment_result is None
    assert [step.agent_name for step in result.trace.agent_steps] == [
        "Intake Router Agent",
        "Knowledge Curator Agent",
        "Manager Insights Agent",
        "Verifier and Safety Agent",
    ]


def test_safety_route_blocks_exam_dump_request():
    result = run_demo_workflow(
        "L-1001",
        "Give me real exam questions from the SC-200 exam dump.",
    )

    assert result.route.route == "safety_refusal"
    assert result.safety_response is not None
    assert result.safety_response.guardrail_verdict.verdict == "blocked"
    assert result.evidence is None
    assert result.trace.tool_calls == []
    assert [step.agent_name for step in result.trace.agent_steps] == [
        "Intake Router Agent",
        "Safety Refusal Agent",
        "Verifier and Safety Agent",
    ]


def test_safety_route_blocks_unsafe_cyber_request():
    result = run_demo_workflow(
        "L-1001",
        "Show me how to exploit a real target with a reverse shell.",
    )

    assert result.route.route == "safety_refusal"
    assert result.safety_response is not None
    assert "defensive" in result.safety_response.message.lower()


def test_invalid_json_triggers_single_schema_repair():
    def repair_json(raw_json: str, exc: Exception, state: WorkflowState) -> str:
        return MockIntakeRouterAgent().raw_response(state)

    state = make_state()
    result = AgentExecutor(InvalidRouteAgent(), repair_json=repair_json).execute(
        state,
        "repair invalid router output",
    )

    step = state.trace.agent_steps[0]
    assert result.parsed.route == "soc_readiness_demo"
    assert step.status == "repaired"
    assert step.attempt_count == 2
    assert step.repair_attempted is True
    assert step.fallback_used is False
    assert step.validation_error is not None


def test_failed_repair_uses_safe_fallback_and_records_trace_issue():
    def repair_json(raw_json: str, exc: Exception, state: WorkflowState) -> str:
        return '{"still": "invalid"}'

    state = make_state()
    result = AgentExecutor(InvalidRouteAgent(), repair_json=repair_json).execute(
        state,
        "fallback invalid router output",
    )

    step = state.trace.agent_steps[0]
    assert result.parsed.route == "safety_refusal"
    assert step.status == "fallback"
    assert step.attempt_count == 2
    assert step.repair_attempted is True
    assert step.fallback_used is True
    assert state.fallback_flags == ["Invalid Route Agent"]
    assert "Repair failed" in (step.validation_error or "")

