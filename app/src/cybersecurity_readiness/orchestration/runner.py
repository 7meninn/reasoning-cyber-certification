from __future__ import annotations

from ..config import RuntimeConfig, load_runtime_config
from ..constants import DEFAULT_DEMO_REQUEST
from ..loader import get_learner
from ..retrieval import FoundryIqRetrievalAdapter, LocalMockRetrievalAdapter
from ..safety import (
    evaluate_input_safety,
    validate_citations,
    validate_citations_against_evidence,
)
from ..schemas import Citation, LearnerLabResponse, RouteDecision, RunTrace, ToolCall, WorkflowResult
from .executor import AgentExecutor
from .registry import build_foundry_agent_registry, build_mock_agent_registry
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
        retrieval_adapter: object | None = None,
        config: RuntimeConfig | None = None,
    ) -> None:
        self.config = config or load_runtime_config()
        if registry is not None:
            self.registry = registry
        elif self.config.foundry_enabled:
            self.registry = build_foundry_agent_registry(self.config)
        else:
            self.registry = build_mock_agent_registry()
        if retrieval_adapter is not None:
            self.retrieval_adapter = retrieval_adapter
        elif self.config.foundry_iq_enabled:
            self.retrieval_adapter = FoundryIqRetrievalAdapter(self.config)
        else:
            self.retrieval_adapter = LocalMockRetrievalAdapter()

    def run(
        self,
        learner_id: str = "L-1001",
        request_text: str = DEFAULT_DEMO_REQUEST,
        selected_lab_id: str | None = None,
        lab_responses: list[LearnerLabResponse] | None = None,
        demo_response_profile: str = "conditional",
    ) -> WorkflowResult:
        learner = get_learner(learner_id)
        state = WorkflowState(
            request_text=request_text,
            learner=learner,
            selected_lab_id=selected_lab_id,
            lab_responses=lab_responses,
            demo_response_profile=demo_response_profile,
            trace=RunTrace(
                run_id=f"RUN-{learner_id}-{self.config.effective_mode.upper()}-001",
                route="pending",
                retrieval_mode=self.config.retrieval_mode,
                fallback_mode=(
                    self.config.effective_mode == "mock"
                    or self.config.fallback_reason is not None
                ),
                requested_app_mode=self.config.requested_mode,
                effective_app_mode=self.config.effective_mode,
                model_mode=self.config.model_mode,
                model_deployment=(
                    self.config.azure_ai_model_deployment
                    if self.config.foundry_enabled
                    else None
                ),
                mode_fallback_reason=self.config.fallback_reason,
                knowledge_base_name=(
                    self.config.foundry_iq_knowledge_base
                    if self.config.foundry_iq_enabled
                    else None
                ),
                selected_lab_id=selected_lab_id,
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
            filters={
                "learner_id": state.learner.learner_id,
                "mode": self.config.effective_mode,
            },
        )
        state.evidence = tool_evidence
        metadata = tool_evidence.retrieval_metadata
        fallback_used = bool(metadata.get("fallback_used", False))
        fallback_reason = metadata.get("fallback_reason")
        if fallback_used:
            state.fallback_flags.append("retrieve_evidence")
            state.trace.retrieval_fallback_reason = str(fallback_reason)
        state.trace.retrieval_mode = tool_evidence.retrieval_mode
        if metadata.get("knowledge_base_name"):
            state.trace.knowledge_base_name = str(metadata["knowledge_base_name"])
        state.trace.tool_calls.append(
            ToolCall(
                tool_name="retrieve_evidence",
                input_summary="Retrieve route evidence",
                output_summary=(
                    f"{len(tool_evidence.citations)} citations returned in "
                    f"{tool_evidence.retrieval_mode} mode"
                ),
                latency_ms=int(metadata.get("latency_ms", 284)),
                retrieval_provider=str(metadata.get("retrieval_provider", "local_mock")),
                retrieval_mode=tool_evidence.retrieval_mode,
                knowledge_base_name=(
                    str(metadata["knowledge_base_name"])
                    if metadata.get("knowledge_base_name")
                    else None
                ),
                source_count=int(metadata.get("source_count", len(tool_evidence.citations))),
                activity_summary=[
                    str(item) for item in metadata.get("activity_summary", [])
                ],
                partial_content=bool(metadata.get("partial_content", False)),
                fallback_used=fallback_used,
                fallback_reason=str(fallback_reason) if fallback_reason else None,
                status_code=(
                    int(metadata["status_code"])
                    if metadata.get("status_code") is not None
                    else None
                ),
            )
        )
        state.trace.latency_ms += int(metadata.get("latency_ms", 284))
        state.trace.citations.extend(tool_evidence.citations)

    def _run_soc_readiness_route(self, state: WorkflowState) -> None:
        self._retrieve_evidence(
            state,
            query=(
                "SOC Analyst Security+ SC-200 suspicious sign-in phishing "
                "vulnerability KQL capacity manager privacy triage"
            ),
        )
        state.evidence = self.registry["knowledge_curator"].execute(
            state, "Retrieve and normalize approved SOC readiness evidence"
        ).parsed
        state.certification_path = self.registry["certification_path_advisor"].execute(
            state, "Map learner profile to Security+ foundation and SC-200 readiness"
        ).parsed
        state.trace.guardrail_verdicts.append(validate_citations(state.certification_path.citations))
        state.trace.guardrail_verdicts.append(
            validate_citations_against_evidence(state.certification_path.citations, state.evidence)
        )
        state.skill_gap_report = self.registry["skill_gap_analyst"].execute(
            state, "Compare learner profile with target SOC readiness domains"
        ).parsed
        state.study_plan = self.registry["study_plan_generator"].execute(
            state, "Generate 4-week capacity-aware plan"
        ).parsed
        state.scenario_lab = self.registry["scenario_lab_coach"].execute(
            state, "Create selected defensive synthetic scenario lab"
        ).parsed
        state.trace.selected_lab_id = state.scenario_lab.lab_id
        state.lab_attempt = self.registry["lab_scoring"].execute(
            state, "Score learner lab responses with deterministic rubric"
        ).parsed
        state.trace.selected_lab_id = state.lab_attempt.lab_id
        state.trace.lab_score = state.lab_attempt.percentage_score
        state.trace.lab_readiness = state.lab_attempt.readiness
        state.trace.adaptive_remediation_reason = (
            state.lab_attempt.adaptive_remediation_reason
        )
        state.assessment_result = self.registry["assessment"].execute(
            state, "Convert lab attempt into readiness verdict and remediation sprint"
        ).parsed
        state.manager_insight = self.registry["manager_insights"].execute(
            state, "Aggregate synthetic team readiness without private learner detail"
        ).parsed
        state.trace.guardrail_verdicts.append(
            validate_citations_against_evidence(state.manager_insight.citations, state.evidence)
        )
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
        state.trace.guardrail_verdicts.append(
            validate_citations_against_evidence(state.manager_insight.citations, state.evidence)
        )
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
