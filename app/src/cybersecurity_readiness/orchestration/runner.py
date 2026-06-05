from __future__ import annotations

from ..constants import DEFAULT_DEMO_REQUEST
from ..loader import get_learner
from ..retrieval import LocalMockRetrievalAdapter
from ..safety import evaluate_input_safety, validate_citations
from ..schemas import Citation, RouteDecision, RunTrace, ToolCall, WorkflowResult
from .executor import AgentExecutor
from .registry import build_mock_agent_registry
from .state import WorkflowState


def _dedupe_citations(citations: list[Citation]) -> list[Citation]:
    seen: set[str] = set()
    unique: list[Citation] = []
    for citation in citations:
        key = citation.source_id
        if key not in seen:
            seen.add(key)
            unique.append(citation)
    return unique


class OrchestratedWorkflowRunner:
    def __init__(
        self,
        registry: dict[str, AgentExecutor] | None = None,
        retrieval_adapter: LocalMockRetrievalAdapter | None = None,
    ) -> None:
        self.registry = registry or build_mock_agent_registry()
        self.retrieval_adapter = retrieval_adapter or LocalMockRetrievalAdapter()

    def run(
        self,
        learner_id: str = "L-1001",
        request_text: str = DEFAULT_DEMO_REQUEST,
    ) -> WorkflowResult:
        learner = get_learner(learner_id)
        state = WorkflowState(
            request_text=request_text,
            learner=learner,
            trace=RunTrace(
                run_id=f"RUN-{learner_id}-MOCK-001",
                route="pending",
                retrieval_mode="local_mock",
                fallback_mode=True,
            ),
        )

        state.input_guardrail = evaluate_input_safety(request_text)
        state.trace.guardrail_verdicts.append(state.input_guardrail)

        state.route = self.registry["intake_router"].execute(
            state=state,
            input_summary="Classify request and choose workflow route",
        ).parsed
        state.trace.route = state.route.route

        if state.route.route == "safety_refusal":
            self._run_safety_route(state)
        elif state.route.route == "manager_insights":
            self._run_manager_route(state)
        else:
            self._run_soc_readiness_route(state)

        state.trace.citations = _dedupe_citations(state.trace.citations)
        state.trace.fallback_mode = bool(state.fallback_flags) or state.trace.fallback_mode
        return state.to_result()

    def _retrieve_evidence(self, state: WorkflowState, query: str) -> None:
        tool_evidence = self.retrieval_adapter.retrieve_evidence(
            query=query,
            filters={"learner_id": state.learner.learner_id, "mode": "mock"},
        )
        state.trace.tool_calls.append(
            ToolCall(
                tool_name="retrieve_evidence",
                input_summary="Local mock retrieval for route evidence",
                output_summary=(
                    f"{len(tool_evidence.citations)} citations returned in "
                    f"{tool_evidence.retrieval_mode} mode"
                ),
                latency_ms=284,
            )
        )
        state.trace.latency_ms += 284
        state.trace.citations.extend(tool_evidence.citations)

    def _run_soc_readiness_route(self, state: WorkflowState) -> None:
        self._retrieve_evidence(
            state,
            query="SOC Analyst Security+ SC-200 suspicious sign-in capacity",
        )
        state.evidence = self.registry["knowledge_curator"].execute(
            state, "Retrieve and normalize approved SOC readiness evidence"
        ).parsed
        state.certification_path = self.registry["certification_path_advisor"].execute(
            state, "Map learner profile to Security+ foundation and SC-200 readiness"
        ).parsed
        state.trace.guardrail_verdicts.append(validate_citations(state.certification_path.citations))
        state.skill_gap_report = self.registry["skill_gap_analyst"].execute(
            state, "Compare learner profile with target SOC readiness domains"
        ).parsed
        state.study_plan = self.registry["study_plan_generator"].execute(
            state, "Generate 4-week capacity-aware plan"
        ).parsed
        state.scenario_lab = self.registry["scenario_lab_coach"].execute(
            state, "Create defensive synthetic suspicious sign-in lab"
        ).parsed
        state.assessment_result = self.registry["assessment"].execute(
            state, "Score partial lab answer and produce readiness verdict"
        ).parsed
        state.manager_insight = self.registry["manager_insights"].execute(
            state, "Aggregate synthetic team readiness without private learner detail"
        ).parsed
        self.registry["verifier_safety"].execute(
            state, "Verify citations, schema validity, safety, and manager privacy"
        )

    def _run_manager_route(self, state: WorkflowState) -> None:
        self._retrieve_evidence(
            state,
            query="manager team readiness capacity privacy SOC certification",
        )
        state.evidence = self.registry["knowledge_curator"].execute(
            state, "Retrieve manager policy and readiness evidence"
        ).parsed
        state.manager_insight = self.registry["manager_insights"].execute(
            state, "Aggregate synthetic team readiness without learner-only steps"
        ).parsed
        state.trace.guardrail_verdicts.append(validate_citations(state.manager_insight.citations))
        self.registry["verifier_safety"].execute(
            state, "Verify manager privacy, citations, and safety"
        )

    def _run_safety_route(self, state: WorkflowState) -> None:
        state.safety_response = self.registry["safety_refusal"].execute(
            state, "Return structured safety refusal and defensive redirect"
        ).parsed
        self.registry["verifier_safety"].execute(
            state, "Verify safety refusal and defensive redirect"
        )
