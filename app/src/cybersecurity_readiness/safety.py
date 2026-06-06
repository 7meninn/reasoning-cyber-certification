from __future__ import annotations

import re
from collections.abc import Sequence

from .schemas import Citation, EvidenceBundle, GuardrailVerdict, StudyPlan


EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@([A-Za-z0-9.-]+\.[A-Za-z]{2,})\b")
SAFE_DEMO_EMAIL_DOMAINS = {"example.com", "example.org", "example.net"}
SECRET_RE = re.compile(
    r"(api[_-]?key\s*[:=]|secret\s*[:=]|password\s*[:=]|connection\s*string|sk-[A-Za-z0-9]{12,})",
    re.IGNORECASE,
)
EXAM_DUMP_RE = re.compile(
    r"(exam\s*dump|brain\s*dump|actual\s+exam\s+questions|real\s+exam\s+questions|leaked\s+questions)",
    re.IGNORECASE,
)
UNSAFE_CYBER_RE = re.compile(
    r"(exploit\s+a\s+real\s+target|hack\s+into|steal\s+credentials|credential\s+theft|"
    r"write\s+malware|ransomware|bypass\s+detection|reverse\s+shell)",
    re.IGNORECASE,
)


def detect_real_pii(text: str) -> bool:
    for match in EMAIL_RE.finditer(text):
        if match.group(1).lower() not in SAFE_DEMO_EMAIL_DOMAINS:
            return True
    return False


def detect_secrets(text: str) -> bool:
    return bool(SECRET_RE.search(text))


def detect_exam_dump_request(text: str) -> bool:
    return bool(EXAM_DUMP_RE.search(text))


def detect_unsafe_cyber_intent(text: str) -> bool:
    return bool(UNSAFE_CYBER_RE.search(text))


def evaluate_input_safety(text: str) -> GuardrailVerdict:
    checks = {
        "no_real_pii": not detect_real_pii(text),
        "no_secrets": not detect_secrets(text),
        "no_exam_dump_request": not detect_exam_dump_request(text),
        "defensive_cyber_intent": not detect_unsafe_cyber_intent(text),
    }
    issues = [name for name, passed in checks.items() if not passed]
    if issues:
        return GuardrailVerdict(
            verdict="blocked",
            issues=issues,
            rewrite_instructions=(
                "Refuse the unsafe request briefly and redirect to defensive, synthetic learning."
            ),
            checks=checks,
        )
    return GuardrailVerdict(verdict="allowed", issues=[], checks=checks)


def validate_citations(citations: Sequence[Citation]) -> GuardrailVerdict:
    checks = {
        "citations_present": bool(citations),
        "citations_have_excerpts": all(bool(citation.excerpt.strip()) for citation in citations),
        "citations_have_titles": all(bool(citation.title.strip()) for citation in citations),
    }
    issues = [name for name, passed in checks.items() if not passed]
    if issues:
        return GuardrailVerdict(
            verdict="rewrite_required",
            issues=issues,
            rewrite_instructions="Add source citations before showing the recommendation.",
            checks=checks,
        )
    return GuardrailVerdict(verdict="allowed", issues=[], checks=checks)


def validate_citations_against_evidence(
    citations: Sequence[Citation],
    evidence: EvidenceBundle | None,
) -> GuardrailVerdict:
    if evidence is None:
        return GuardrailVerdict(
            verdict="rewrite_required",
            issues=["no_retrieved_evidence_available"],
            rewrite_instructions="Use retrieved evidence before making citation-backed claims.",
            checks={"citations_grounded_in_retrieval": False},
        )

    allowed = {citation.source_id for citation in evidence.citations}
    cited = {citation.source_id for citation in citations}
    unsupported = sorted(cited - allowed)
    if unsupported:
        return GuardrailVerdict(
            verdict="rewrite_required",
            issues=[f"unsupported_citations:{','.join(unsupported)}"],
            rewrite_instructions="Use only citations returned by the retrieval adapter.",
            checks={
                "citations_grounded_in_retrieval": False,
                "retrieved_citation_count": bool(allowed),
            },
        )
    return GuardrailVerdict(
        verdict="allowed",
        issues=[],
        rewrite_instructions=None,
        checks={
            "citations_grounded_in_retrieval": True,
            "retrieved_citation_count": bool(allowed),
        },
    )


def plan_fits_capacity(plan: StudyPlan) -> bool:
    return (
        plan.workload_fit.fit != "overloaded"
        and plan.workload_fit.planned_hours_per_week
        <= plan.workload_fit.available_focus_hours_per_week
    )
