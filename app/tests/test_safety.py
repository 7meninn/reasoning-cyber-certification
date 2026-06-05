from cybersecurity_readiness.safety import (
    detect_real_pii,
    detect_secrets,
    evaluate_input_safety,
)


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
