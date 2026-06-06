from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Citation(StrictModel):
    source_id: str
    title: str
    source_type: Literal[
        "official_public_summary",
        "synthetic_internal",
        "synthetic_lab",
        "synthetic_policy",
    ]
    url: str | None = None
    excerpt: str
    metadata: dict[str, str] = Field(default_factory=dict)

    @field_validator("excerpt")
    @classmethod
    def excerpt_must_be_present(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("citation excerpt is required")
        return value


class LearnerProfile(StrictModel):
    learner_id: str
    employee_id: str
    role_current: str
    role_target: str
    experience_level: str
    completed_certifications: list[str]
    preferred_learning_style: str
    available_focus_hours_per_week: int = Field(ge=0, le=40)
    constraints: list[str] = Field(default_factory=list)
    skills_self_rating: dict[str, int]

    @field_validator("skills_self_rating")
    @classmethod
    def ratings_must_be_zero_to_five(cls, value: dict[str, int]) -> dict[str, int]:
        for skill, score in value.items():
            if score < 0 or score > 5:
                raise ValueError(f"{skill} score must be between 0 and 5")
        return value


class RouteDecision(StrictModel):
    route: Literal["soc_readiness_demo", "manager_insights", "safety_refusal"]
    learner_id: str
    goal: str
    risk_flags: list[str]
    next_agents: list[str]
    confidence: float = Field(ge=0, le=1)


class EvidenceBundle(StrictModel):
    query: str
    sources: list[Citation]
    snippets: list[str]
    citations: list[Citation]
    retrieval_mode: Literal["foundry_iq", "azure_ai_search", "local_mock"]
    confidence: float = Field(ge=0, le=1)
    missing_evidence_warning: str | None = None
    retrieval_metadata: dict[str, Any] = Field(default_factory=dict)


class CertificationPath(StrictModel):
    target_role: str
    recommended_certifications: list[str]
    sequence: list[str]
    prerequisites: list[str]
    rationale: str
    caveats: list[str]
    alternate_paths: list[str]
    citations: list[Citation]
    confidence: float = Field(ge=0, le=1)


class SkillDomainScore(StrictModel):
    domain: str
    current_score: int = Field(ge=0, le=100)
    target_score: int = Field(ge=0, le=100)
    priority: Literal["High", "Medium", "Low"]
    evidence: str
    citations: list[Citation]


class SkillGapReport(StrictModel):
    learner_id: str
    target_certification: str
    domain_scores: list[SkillDomainScore]
    priority_gaps: list[str]
    strengths: list[str]
    risk_level: Literal["Low", "Medium", "High"]
    recommended_focus: list[str]
    citations: list[Citation]
    confidence: float = Field(ge=0, le=1)


class StudyTask(StrictModel):
    day: str
    title: str
    duration_minutes: int = Field(gt=0, le=240)
    activity_type: Literal["reading", "lab", "practice", "review", "assessment"]
    outcome: str
    citations: list[Citation] = Field(default_factory=list)


class WeekPlan(StrictModel):
    week: int = Field(ge=1, le=12)
    theme: str
    total_hours: float = Field(gt=0, le=20)
    tasks: list[StudyTask]
    scenario_lab: str
    checkpoint: str


class WorkloadFit(StrictModel):
    available_focus_hours_per_week: int = Field(ge=0, le=40)
    planned_hours_per_week: float = Field(gt=0, le=40)
    fit: Literal["fits", "tight", "overloaded"]
    rationale: str


class StudyPlan(StrictModel):
    learner_id: str
    duration_weeks: int = Field(ge=1, le=12)
    weekly_modules: list[WeekPlan]
    workload_fit: WorkloadFit
    checkpoints: list[str]
    citations: list[Citation]
    confidence: float = Field(ge=0, le=1)


class LabArtifact(StrictModel):
    artifact_type: str
    name: str
    content: str


class RubricItem(StrictModel):
    criterion: str
    max_points: int = Field(gt=0, le=10)
    expected_signal: str


class ScenarioLab(StrictModel):
    lab_id: str
    title: str
    domain: str
    prompt: str
    artifacts: list[LabArtifact]
    learner_task: str
    expected_investigation_path: list[str]
    rubric: list[RubricItem]
    safety_note: str
    citations: list[Citation]


class RemediationTask(StrictModel):
    title: str
    focus_domain: str
    duration_minutes: int = Field(gt=0, le=240)
    outcome: str


class RemediationPlan(StrictModel):
    duration_days: int = Field(ge=1, le=14)
    tasks: list[RemediationTask]
    success_criteria: list[str]


class AssessmentResult(StrictModel):
    learner_id: str
    overall_readiness: Literal["GO", "CONDITIONAL", "NOT_YET"]
    overall_score: int = Field(ge=0, le=100)
    domain_scores: dict[str, int]
    recommendation: str
    evidence: list[str]
    remediation_plan: RemediationPlan
    citations: list[Citation]
    confidence: float = Field(ge=0, le=1)

    @field_validator("domain_scores")
    @classmethod
    def domain_scores_must_be_percentages(cls, value: dict[str, int]) -> dict[str, int]:
        for domain, score in value.items():
            if score < 0 or score > 100:
                raise ValueError(f"{domain} score must be between 0 and 100")
        return value


class ManagerInsight(StrictModel):
    team_id: str
    summary: str
    readiness_distribution: dict[str, int]
    top_skill_gaps: list[str]
    capacity_risk: Literal["Low", "Medium", "High"]
    recommended_actions: list[str]
    privacy_note: str
    citations: list[Citation]
    confidence: float = Field(ge=0, le=1)


class GuardrailVerdict(StrictModel):
    verdict: Literal["allowed", "rewrite_required", "blocked"]
    issues: list[str]
    rewrite_instructions: str | None = None
    checks: dict[str, bool]


class SafetyResponse(StrictModel):
    route: Literal["safety_refusal"] = "safety_refusal"
    message: str
    safe_alternatives: list[str]
    guardrail_verdict: GuardrailVerdict


class ToolCall(StrictModel):
    tool_name: str
    input_summary: str
    output_summary: str
    latency_ms: int = Field(ge=0)
    retrieval_provider: str | None = None
    retrieval_mode: Literal["foundry_iq", "azure_ai_search", "local_mock"] | None = None
    knowledge_base_name: str | None = None
    source_count: int | None = Field(default=None, ge=0)
    activity_summary: list[str] = Field(default_factory=list)
    partial_content: bool = False
    fallback_used: bool = False
    fallback_reason: str | None = None
    status_code: int | None = Field(default=None, ge=100, le=599)


class AgentStep(StrictModel):
    agent_name: str
    latency_ms: int = Field(ge=0)
    input_summary: str
    raw_json_response: str | None = None
    parsed_output: dict[str, Any]
    citations: list[Citation] = Field(default_factory=list)
    guardrail_verdicts: list[GuardrailVerdict] = Field(default_factory=list)
    retrieval_mode: Literal["foundry_iq", "azure_ai_search", "local_mock"] | None = None
    status: Literal["success", "repaired", "fallback", "blocked"] = "success"
    attempt_count: int = Field(default=1, ge=1)
    repair_attempted: bool = False
    fallback_used: bool = False
    validation_error: str | None = None
    repair_notes: str | None = None
    model_mode: Literal["mock", "foundry"] | None = None
    model_deployment: str | None = None
    model_request_id: str | None = None
    model_finish_reason: str | None = None
    token_usage: dict[str, int] | None = None
    fallback_reason: str | None = None


class RunTrace(StrictModel):
    run_id: str
    route: str
    agent_steps: list[AgentStep] = Field(default_factory=list)
    tool_calls: list[ToolCall] = Field(default_factory=list)
    citations: list[Citation] = Field(default_factory=list)
    guardrail_verdicts: list[GuardrailVerdict] = Field(default_factory=list)
    latency_ms: int = Field(default=0, ge=0)
    retrieval_mode: Literal["foundry_iq", "azure_ai_search", "local_mock"] = "local_mock"
    fallback_mode: bool = True
    requested_app_mode: Literal["mock", "foundry", "foundry_iq"] = "mock"
    effective_app_mode: Literal["mock", "foundry", "foundry_iq"] = "mock"
    model_mode: Literal["mock", "foundry"] = "mock"
    model_deployment: str | None = None
    mode_fallback_reason: str | None = None
    knowledge_base_name: str | None = None
    retrieval_fallback_reason: str | None = None


class WorkflowResult(StrictModel):
    learner: LearnerProfile
    route: RouteDecision
    evidence: EvidenceBundle | None = None
    certification_path: CertificationPath | None = None
    skill_gap_report: SkillGapReport | None = None
    study_plan: StudyPlan | None = None
    scenario_lab: ScenarioLab | None = None
    assessment_result: AssessmentResult | None = None
    manager_insight: ManagerInsight | None = None
    safety_response: SafetyResponse | None = None
    trace: RunTrace
