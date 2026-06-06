from __future__ import annotations

import re
from collections import defaultdict

from .safety import evaluate_input_safety
from .schemas import (
    Citation,
    GuardrailVerdict,
    LabAttempt,
    LabQuestion,
    LabScoreBreakdown,
    LearnerLabResponse,
    ScenarioLab,
)


ResponseProfile = str
PROFILE_GO = "go"
PROFILE_CONDITIONAL = "conditional"
PROFILE_NOT_YET = "not_yet"
PROFILE_CUSTOM = "custom"


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower()).strip()


def _dedupe_citations(citations: list[Citation]) -> list[Citation]:
    seen: set[str] = set()
    unique: list[Citation] = []
    for citation in citations:
        if citation.source_id not in seen:
            seen.add(citation.source_id)
            unique.append(citation)
    return unique


def _question_response(
    question: LabQuestion,
    profile: ResponseProfile,
) -> LearnerLabResponse:
    expected = list(question.expected_option_ids)
    wrong_options = [
        option.option_id
        for option in question.options
        if option.option_id not in set(question.expected_option_ids)
    ]

    if profile == PROFILE_GO:
        return LearnerLabResponse(
            question_id=question.question_id,
            selected_option_ids=expected,
            free_text=" ".join(question.expected_keywords),
        )

    if profile == PROFILE_NOT_YET:
        return LearnerLabResponse(
            question_id=question.question_id,
            selected_option_ids=wrong_options[:1],
            free_text="I would close the alert without preserving more evidence.",
        )

    selected_option_ids: list[str] = []
    if question.response_type == "single_choice":
        selected_option_ids = expected[:1]
    elif question.response_type == "multi_select":
        selected_option_ids = expected[:1]
    keyword_count = max(1, len(question.expected_keywords) // 2)
    return LearnerLabResponse(
        question_id=question.question_id,
        selected_option_ids=selected_option_ids,
        free_text=" ".join(question.expected_keywords[:keyword_count]),
    )


def get_demo_lab_responses(
    lab: ScenarioLab,
    profile: ResponseProfile = PROFILE_CONDITIONAL,
) -> list[LearnerLabResponse]:
    normalized_profile = profile if profile in {PROFILE_GO, PROFILE_NOT_YET} else PROFILE_CONDITIONAL
    return [_question_response(question, normalized_profile) for question in lab.questions]


def validate_lab_responses_against_lab(
    lab: ScenarioLab,
    responses: list[LearnerLabResponse],
) -> GuardrailVerdict:
    questions = {question.question_id: question for question in lab.questions}
    issues: list[str] = []
    checks = {
        "known_questions": True,
        "known_options": True,
        "single_choice_shape": True,
        "safe_lab_response_text": True,
    }

    for response in responses:
        question = questions.get(response.question_id)
        if question is None:
            checks["known_questions"] = False
            issues.append(f"unknown_question:{response.question_id}")
            continue

        option_ids = {option.option_id for option in question.options}
        unknown_options = sorted(set(response.selected_option_ids) - option_ids)
        if unknown_options:
            checks["known_options"] = False
            issues.append(
                f"invalid_option_reference:{response.question_id}:{','.join(unknown_options)}"
            )
        if question.response_type == "single_choice" and len(response.selected_option_ids) > 1:
            checks["single_choice_shape"] = False
            issues.append(f"single_choice_multiple_options:{response.question_id}")

        text_verdict = evaluate_input_safety(response.free_text)
        if text_verdict.verdict == "blocked":
            checks["safe_lab_response_text"] = False
            issues.extend(text_verdict.issues)

    if issues:
        return GuardrailVerdict(
            verdict="blocked",
            issues=sorted(set(issues)),
            rewrite_instructions=(
                "Refuse unsafe or malformed lab responses and reset to defensive synthetic practice."
            ),
            checks=checks,
        )

    return GuardrailVerdict(verdict="allowed", issues=[], checks=checks)


def _score_choice_question(
    question: LabQuestion,
    response: LearnerLabResponse,
) -> tuple[int, list[str]]:
    expected = set(question.expected_option_ids)
    selected = set(response.selected_option_ids)
    if selected == expected:
        return question.points, []

    overlap = len(selected & expected)
    false_positives = len(selected - expected)
    earned = int(question.points * (overlap / max(1, len(expected))))
    earned = max(0, earned - false_positives)
    missed = [f"Select option {option_id}" for option_id in sorted(expected - selected)]
    if false_positives:
        missed.append("Avoid unrelated or overbroad actions")
    return earned, missed


def _score_free_text_question(
    question: LabQuestion,
    response: LearnerLabResponse,
) -> tuple[int, list[str]]:
    text = _normalize(response.free_text)
    hits = [
        keyword
        for keyword in question.expected_keywords
        if _normalize(keyword) in text
    ]
    earned = int(question.points * (len(hits) / max(1, len(question.expected_keywords))))
    missed = [
        f"Include signal: {keyword}"
        for keyword in question.expected_keywords
        if keyword not in hits
    ]
    return earned, missed


def _score_question(
    question: LabQuestion,
    response: LearnerLabResponse,
) -> tuple[int, list[str]]:
    if question.response_type == "free_text":
        return _score_free_text_question(question, response)
    return _score_choice_question(question, response)


def _readiness_from_score(percentage_score: int) -> str:
    if percentage_score >= 85:
        return "GO"
    if percentage_score >= 60:
        return "CONDITIONAL"
    return "NOT_YET"


def _blocked_attempt(
    *,
    lab: ScenarioLab,
    learner_id: str,
    responses: list[LearnerLabResponse],
    response_profile: ResponseProfile,
    guardrail_verdict: GuardrailVerdict,
) -> LabAttempt:
    citations = _dedupe_citations(lab.citations)
    max_score = sum(question.points for question in lab.questions) or 1
    score_breakdown = [
        LabScoreBreakdown(
            question_id=question.question_id,
            domain=question.domain,
            criterion=question.prompt,
            earned_points=0,
            max_points=question.points,
            feedback="Response was blocked by safety or lab-shape validation.",
            missed_signals=["Use only safe synthetic defensive lab responses."],
            citations=question.citations or lab.citations,
        )
        for question in lab.questions
    ]
    return LabAttempt(
        lab_id=lab.lab_id,
        learner_id=learner_id,
        response_profile=response_profile,  # type: ignore[arg-type]
        responses=responses,
        score_breakdown=score_breakdown,
        total_score=0,
        max_score=max_score,
        percentage_score=0,
        readiness="NOT_YET",
        domain_scores={question.domain: 0 for question in lab.questions},
        mistakes_by_domain={
            question.domain: ["Unsafe or malformed response blocked."]
            for question in lab.questions
        },
        remediation_focus=sorted({question.domain for question in lab.questions}),
        adaptive_remediation_reason=(
            "Lab response was blocked, so the remediation sprint redirects to safe synthetic practice."
        ),
        guardrail_verdict=guardrail_verdict,
        citations=citations,
        confidence=0.99,
    )


def score_lab_attempt(
    *,
    lab: ScenarioLab,
    learner_id: str,
    responses: list[LearnerLabResponse] | None = None,
    response_profile: ResponseProfile = PROFILE_CONDITIONAL,
) -> LabAttempt:
    profile = response_profile if response_profile in {PROFILE_GO, PROFILE_CONDITIONAL, PROFILE_NOT_YET} else PROFILE_CUSTOM
    selected_responses = responses or get_demo_lab_responses(lab, profile)
    if responses is not None:
        profile = PROFILE_CUSTOM

    guardrail_verdict = validate_lab_responses_against_lab(lab, selected_responses)
    if guardrail_verdict.verdict == "blocked":
        return _blocked_attempt(
            lab=lab,
            learner_id=learner_id,
            responses=selected_responses,
            response_profile=profile,
            guardrail_verdict=guardrail_verdict,
        )

    responses_by_question = {
        response.question_id: response
        for response in selected_responses
    }
    breakdown: list[LabScoreBreakdown] = []
    citations: list[Citation] = list(lab.citations)
    domain_earned: dict[str, int] = defaultdict(int)
    domain_max: dict[str, int] = defaultdict(int)
    mistakes_by_domain: dict[str, list[str]] = defaultdict(list)

    for question in lab.questions:
        response = responses_by_question.get(
            question.question_id,
            LearnerLabResponse(question_id=question.question_id),
        )
        earned_points, missed_signals = _score_question(question, response)
        question_citations = question.citations or lab.citations
        citations.extend(question_citations)
        domain_earned[question.domain] += earned_points
        domain_max[question.domain] += question.points
        if missed_signals:
            mistakes_by_domain[question.domain].extend(missed_signals)

        feedback = (
            "Strong response aligned with the expected investigation signal."
            if earned_points == question.points
            else question.explanation
        )
        breakdown.append(
            LabScoreBreakdown(
                question_id=question.question_id,
                domain=question.domain,
                criterion=question.prompt,
                earned_points=earned_points,
                max_points=question.points,
                feedback=feedback,
                missed_signals=missed_signals,
                citations=question_citations,
            )
        )

    total_score = sum(item.earned_points for item in breakdown)
    max_score = sum(item.max_points for item in breakdown) or 1
    percentage_score = round((total_score / max_score) * 100)
    readiness = _readiness_from_score(percentage_score)
    domain_scores = {
        domain: round((domain_earned[domain] / domain_max[domain]) * 100)
        for domain in sorted(domain_max)
    }
    remediation_focus = [
        domain
        for domain, score in sorted(domain_scores.items(), key=lambda item: item[1])
        if score < 75
    ]
    if not remediation_focus and readiness != "GO":
        remediation_focus = [lab.domain]

    reason = (
        "Lab score is GO; keep the study plan steady and use final review practice."
        if readiness == "GO"
        else (
            "Lab score is CONDITIONAL; remediation targets the weakest domain signals."
            if readiness == "CONDITIONAL"
            else "Lab score is NOT_YET; remediation loops back through fundamentals and guided practice."
        )
    )

    return LabAttempt(
        lab_id=lab.lab_id,
        learner_id=learner_id,
        response_profile=profile,  # type: ignore[arg-type]
        responses=selected_responses,
        score_breakdown=breakdown,
        total_score=total_score,
        max_score=max_score,
        percentage_score=percentage_score,
        readiness=readiness,  # type: ignore[arg-type]
        domain_scores=domain_scores,
        mistakes_by_domain={key: value for key, value in mistakes_by_domain.items()},
        remediation_focus=remediation_focus,
        adaptive_remediation_reason=reason,
        guardrail_verdict=guardrail_verdict,
        citations=_dedupe_citations(citations),
        confidence=0.91,
    )
