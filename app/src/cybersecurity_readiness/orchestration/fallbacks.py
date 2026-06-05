from __future__ import annotations

from typing import Any

from ..schemas import (
    AssessmentResult,
    CertificationPath,
    Citation,
    EvidenceBundle,
    GuardrailVerdict,
    ManagerInsight,
    RemediationPlan,
    RouteDecision,
    SafetyResponse,
    ScenarioLab,
    SkillGapReport,
    StudyPlan,
    WorkloadFit,
)


def fallback_citation() -> Citation:
    return Citation(
        source_id="FALLBACK-LOCAL",
        title="Local deterministic fallback",
        source_type="synthetic_internal",
        url=None,
        excerpt="Fallback output generated locally after schema validation failed.",
        metadata={"synthetic": "true", "fallback": "true"},
    )


def fallback_guardrail(issue: str) -> GuardrailVerdict:
    return GuardrailVerdict(
        verdict="rewrite_required",
        issues=[issue],
        rewrite_instructions="Use a safe deterministic fallback and preserve trace evidence.",
        checks={"schema_valid": False, "fallback_used": True},
    )


def blocked_guardrail(issues: list[str]) -> GuardrailVerdict:
    return GuardrailVerdict(
        verdict="blocked",
        issues=issues,
        rewrite_instructions="Refuse briefly and redirect to defensive, synthetic learning.",
        checks={
            "no_real_pii": "no_real_pii" not in issues,
            "no_secrets": "no_secrets" not in issues,
            "no_exam_dump_request": "no_exam_dump_request" not in issues,
            "defensive_cyber_intent": "defensive_cyber_intent" not in issues,
        },
    )


def fallback_for_schema(schema: type[Any], reason: str) -> Any:
    citation = fallback_citation()
    if schema is RouteDecision:
        return RouteDecision(
            route="safety_refusal",
            learner_id="L-1001",
            goal="Fallback route after invalid router output.",
            risk_flags=[reason],
            next_agents=["Safety Refusal Agent", "Verifier and Safety Agent"],
            confidence=0.1,
        )
    if schema is EvidenceBundle:
        return EvidenceBundle(
            query="fallback",
            sources=[citation],
            snippets=["Fallback local evidence used because schema validation failed."],
            citations=[citation],
            retrieval_mode="local_mock",
            confidence=0.1,
            missing_evidence_warning=reason,
        )
    if schema is CertificationPath:
        return CertificationPath(
            target_role="SOC Analyst",
            recommended_certifications=["Security+ foundation", "SC-200-oriented readiness"],
            sequence=["Use local fallback path", "Review citations before final recommendation"],
            prerequisites=["Basic security concepts"],
            rationale="Fallback certification path used after schema validation failed.",
            caveats=["Fallback output requires review."],
            alternate_paths=[],
            citations=[citation],
            confidence=0.1,
        )
    if schema is SkillGapReport:
        return SkillGapReport(
            learner_id="L-1001",
            target_certification="SC-200-oriented SOC readiness",
            domain_scores=[],
            priority_gaps=["Schema validation recovery"],
            strengths=[],
            risk_level="High",
            recommended_focus=["Rerun deterministic workflow after fixing agent output"],
            citations=[citation],
            confidence=0.1,
        )
    if schema is StudyPlan:
        return StudyPlan(
            learner_id="L-1001",
            duration_weeks=1,
            weekly_modules=[],
            workload_fit=WorkloadFit(
                available_focus_hours_per_week=6,
                planned_hours_per_week=1,
                fit="fits",
                rationale="Fallback plan keeps load minimal until valid output is restored.",
            ),
            checkpoints=["Fix agent output schema"],
            citations=[citation],
            confidence=0.1,
        )
    if schema is ScenarioLab:
        return ScenarioLab(
            lab_id="LAB-FALLBACK",
            title="Fallback defensive review",
            domain="Safety and schema recovery",
            prompt="Review the synthetic data statement and rerun the workflow.",
            artifacts=[],
            learner_task="Confirm the demo remains defensive and synthetic.",
            expected_investigation_path=["Do not infer real systems", "Repair invalid agent output"],
            rubric=[],
            safety_note="Fallback defensive content only.",
            citations=[citation],
        )
    if schema is AssessmentResult:
        return AssessmentResult(
            learner_id="L-1001",
            overall_readiness="NOT_YET",
            overall_score=0,
            domain_scores={},
            recommendation="Fallback assessment used after schema validation failed.",
            evidence=[reason],
            remediation_plan=RemediationPlan(
                duration_days=1,
                tasks=[],
                success_criteria=["Restore valid agent JSON"],
            ),
            citations=[citation],
            confidence=0.1,
        )
    if schema is ManagerInsight:
        return ManagerInsight(
            team_id="TEAM-SOC-A",
            summary="Fallback manager insight used after schema validation failed.",
            readiness_distribution={"GO": 0, "CONDITIONAL": 0, "NOT_YET": 0},
            top_skill_gaps=["Schema validation recovery"],
            capacity_risk="High",
            recommended_actions=["Repair invalid manager insight output"],
            privacy_note="Fallback preserves privacy and synthetic-only data boundaries.",
            citations=[citation],
            confidence=0.1,
        )
    if schema is GuardrailVerdict:
        return fallback_guardrail(reason)
    if schema is SafetyResponse:
        return SafetyResponse(
            message="I cannot help with that request. I can help with defensive synthetic cybersecurity learning.",
            safe_alternatives=["Run a synthetic SOC lab", "Create a defensive study plan"],
            guardrail_verdict=blocked_guardrail([reason]),
        )
    raise TypeError(f"No fallback registered for schema {schema.__name__}.")

