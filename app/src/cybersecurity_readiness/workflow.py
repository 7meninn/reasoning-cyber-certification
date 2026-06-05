from __future__ import annotations

from .agents import (
    MockAssessmentAgent,
    MockCertificationPathAdvisorAgent,
    MockIntakeRouterAgent,
    MockKnowledgeCuratorAgent,
    MockManagerInsightsAgent,
    MockScenarioLabCoachAgent,
    MockSkillGapAnalystAgent,
    MockStudyPlanGeneratorAgent,
    MockVerifierSafetyAgent,
)
from .loader import get_learner
from .retrieval import LocalMockRetrievalAdapter
from .safety import evaluate_input_safety, validate_citations
from .schemas import Citation, RunTrace, ToolCall, WorkflowResult


DEFAULT_DEMO_REQUEST = (
    "I am a helpdesk analyst with basic networking knowledge. I want to become "
    "a SOC analyst in 4 weeks and can study 6 hours per week."
)


def _dedupe_citations(citations: list[Citation]) -> list[Citation]:
    seen: set[str] = set()
    unique: list[Citation] = []
    for citation in citations:
        key = citation.source_id
        if key not in seen:
            seen.add(key)
            unique.append(citation)
    return unique


def run_demo_workflow(
    learner_id: str = "L-1001",
    request_text: str = DEFAULT_DEMO_REQUEST,
) -> WorkflowResult:
    learner = get_learner(learner_id)
    trace = RunTrace(
        run_id=f"RUN-{learner_id}-MOCK-001",
        route="pending",
        retrieval_mode="local_mock",
        fallback_mode=True,
    )

    input_guardrail = evaluate_input_safety(request_text)
    trace.guardrail_verdicts.append(input_guardrail)
    if input_guardrail.verdict == "blocked":
        raise ValueError("Demo request was blocked by safety guardrails.")

    retrieval_adapter = LocalMockRetrievalAdapter()
    tool_evidence = retrieval_adapter.retrieve_evidence(
        query="SOC Analyst Security+ SC-200 suspicious sign-in capacity",
        filters={"learner_id": learner_id, "mode": "mock"},
    )
    trace.tool_calls.append(
        ToolCall(
            tool_name="retrieve_evidence",
            input_summary="Local mock retrieval for SOC readiness sources",
            output_summary=(
                f"{len(tool_evidence.citations)} citations returned in "
                f"{tool_evidence.retrieval_mode} mode"
            ),
            latency_ms=284,
        )
    )
    trace.latency_ms += 284
    trace.citations.extend(tool_evidence.citations)

    route = MockIntakeRouterAgent().run(
        trace=trace,
        input_summary="Classify learner request and select SOC readiness route",
    ).parsed
    trace.route = route.route

    evidence = MockKnowledgeCuratorAgent().run(
        trace=trace,
        input_summary="Retrieve and normalize approved SOC readiness evidence",
    ).parsed

    certification_path = MockCertificationPathAdvisorAgent().run(
        trace=trace,
        input_summary="Map learner profile to Security+ foundation and SC-200 readiness",
    ).parsed
    trace.guardrail_verdicts.append(validate_citations(certification_path.citations))

    skill_gap_report = MockSkillGapAnalystAgent().run(
        trace=trace,
        input_summary="Compare L-1001 profile with target SOC readiness domains",
    ).parsed

    study_plan = MockStudyPlanGeneratorAgent().run(
        trace=trace,
        input_summary="Generate 4-week capacity-aware plan for 6 focus hours per week",
    ).parsed

    scenario_lab = MockScenarioLabCoachAgent().run(
        trace=trace,
        input_summary="Create defensive synthetic suspicious sign-in lab",
    ).parsed

    assessment_result = MockAssessmentAgent().run(
        trace=trace,
        input_summary="Score partial lab answer and produce readiness verdict",
    ).parsed

    manager_insight = MockManagerInsightsAgent().run(
        trace=trace,
        input_summary="Aggregate synthetic team readiness without private learner detail",
    ).parsed

    MockVerifierSafetyAgent().run(
        trace=trace,
        input_summary="Verify citations, schema validity, safety, and manager privacy",
    )

    trace.citations = _dedupe_citations(trace.citations)

    return WorkflowResult(
        learner=learner,
        route=route,
        evidence=evidence,
        certification_path=certification_path,
        skill_gap_report=skill_gap_report,
        study_plan=study_plan,
        scenario_lab=scenario_lab,
        assessment_result=assessment_result,
        manager_insight=manager_insight,
        trace=trace,
    )

