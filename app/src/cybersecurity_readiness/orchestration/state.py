from __future__ import annotations

from dataclasses import dataclass, field

from ..schemas import (
    AssessmentResult,
    CertificationPath,
    EvidenceBundle,
    GuardrailVerdict,
    LearnerProfile,
    ManagerInsight,
    RouteDecision,
    RunTrace,
    SafetyResponse,
    ScenarioLab,
    SkillGapReport,
    StudyPlan,
    WorkflowResult,
)


@dataclass
class WorkflowState:
    request_text: str
    learner: LearnerProfile
    trace: RunTrace
    input_guardrail: GuardrailVerdict | None = None
    route: RouteDecision | None = None
    evidence: EvidenceBundle | None = None
    certification_path: CertificationPath | None = None
    skill_gap_report: SkillGapReport | None = None
    study_plan: StudyPlan | None = None
    scenario_lab: ScenarioLab | None = None
    assessment_result: AssessmentResult | None = None
    manager_insight: ManagerInsight | None = None
    safety_response: SafetyResponse | None = None
    errors: list[str] = field(default_factory=list)
    fallback_flags: list[str] = field(default_factory=list)

    def require_route(self) -> RouteDecision:
        if self.route is None:
            raise RuntimeError("Workflow route was not set.")
        return self.route

    def to_result(self) -> WorkflowResult:
        return WorkflowResult(
            learner=self.learner,
            route=self.require_route(),
            evidence=self.evidence,
            certification_path=self.certification_path,
            skill_gap_report=self.skill_gap_report,
            study_plan=self.study_plan,
            scenario_lab=self.scenario_lab,
            assessment_result=self.assessment_result,
            manager_insight=self.manager_insight,
            safety_response=self.safety_response,
            trace=self.trace,
        )

