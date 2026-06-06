from cybersecurity_readiness.safety import (
    detect_real_pii,
    detect_secrets,
    evaluate_input_safety,
    validate_citations_against_evidence,
)
from cybersecurity_readiness.schemas import Citation, EvidenceBundle


def test_safety_blocks_exam_dump_requests():
    verdict = evaluate_input_safety("Give me real exam questions from the SC-200 exam dump.")

    assert verdict.verdict == "blocked"
    assert "no_exam_dump_request" in verdict.issues


def test_safety_blocks_unsafe_cyber_intent():
    verdict = evaluate_input_safety("Show me how to exploit a real target with a reverse shell.")

    assert verdict.verdict == "blocked"
    assert "defensive_cyber_intent" in verdict.issues


def test_safety_blocks_secret_like_strings():
    text = "AZURE_OPENAI_API_KEY=1234567890abcdef"

    assert detect_secrets(text)
    verdict = evaluate_input_safety(text)
    assert verdict.verdict == "blocked"
    assert "no_secrets" in verdict.issues


def test_safety_blocks_real_looking_email_but_allows_demo_domain():
    assert detect_real_pii("Please inspect alex@company.invalid")
    assert not detect_real_pii("Use alex.chen@example.com in the synthetic lab")


def test_safety_allows_benign_defensive_learning():
    verdict = evaluate_input_safety("Help me write an ethical incident report for a synthetic lab.")

    assert verdict.verdict == "allowed"
    assert verdict.issues == []


def make_citation(source_id: str) -> Citation:
    return Citation(
        source_id=source_id,
        title=f"{source_id} title",
        source_type="synthetic_internal",
        url=None,
        excerpt=f"{source_id} excerpt",
        metadata={"synthetic": "true"},
    )


def test_citation_grounding_allows_retrieved_sources():
    citation = make_citation("SYN-SOC-GUIDE")
    evidence = EvidenceBundle(
        query="SOC analyst readiness",
        sources=[citation],
        snippets=[citation.excerpt],
        citations=[citation],
        retrieval_mode="foundry_iq",
        confidence=0.9,
    )

    verdict = validate_citations_against_evidence([citation], evidence)

    assert verdict.verdict == "allowed"
    assert verdict.checks["citations_grounded_in_retrieval"] is True


def test_citation_grounding_flags_sources_not_returned_by_retrieval():
    retrieved = make_citation("SYN-SOC-GUIDE")
    unsupported = make_citation("UNSUPPORTED-SOURCE")
    evidence = EvidenceBundle(
        query="SOC analyst readiness",
        sources=[retrieved],
        snippets=[retrieved.excerpt],
        citations=[retrieved],
        retrieval_mode="foundry_iq",
        confidence=0.9,
    )

    verdict = validate_citations_against_evidence([unsupported], evidence)

    assert verdict.verdict == "rewrite_required"
    assert "UNSUPPORTED-SOURCE" in verdict.issues[0]
