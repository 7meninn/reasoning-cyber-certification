# Evaluation

## Current Phase 5 Evidence

The Phase 5 implementation keeps deterministic mock mode as the default, preserves optional Foundry-backed model agents and optional Foundry IQ retrieval, and adds interactive deterministic scenario labs with adaptive assessment. CI does not make live Azure calls.

Current local test result:

```text
57 passed
```

## What The Tests Cover

- Pydantic schema validation for typed agent handoffs.
- Deterministic mock agents returning raw JSON strings before parsing.
- A guard test that fails if a mock agent bypasses JSON parsing with a Python dictionary.
- Local mock retrieval with explicit `retrieval_mode = local_mock`.
- Citation presence and citation shape validation.
- Safety checks for exam dumps, unsafe cyber intent, secret-like strings, and real-looking PII.
- Golden path for learner `L-1001`: route, evidence, path, gaps, plan, lab, assessment, manager insight, and trace.
- Multi-agent orchestration route order for SOC learner flow.
- Manager route that skips learner-only planning, lab, and assessment steps.
- Safety route that returns a structured defensive refusal.
- Schema repair attempt and safe fallback when repair fails.
- Runtime config tests for default mock mode, valid Foundry mode, missing Foundry env fallback, and unsupported mode fallback.
- Runtime config tests for valid Foundry IQ mode and missing Foundry IQ env fallback.
- Fake Foundry IQ retrieval tests for valid response mapping, partial content, empty citations, malformed response, auth failure, and timeout fallback.
- Citation grounding tests proving agent citations can be checked against retrieved evidence.
- Foundry IQ golden path using a fake adapter: route, live evidence, path, gaps, plan, lab, assessment, manager insight, and trace.
- Synthetic lab catalog validation for suspicious sign-in, phishing triage, vulnerability prioritization, and KQL interpretation.
- Deterministic scoring tests for GO, CONDITIONAL, and NOT_YET lab attempts.
- Custom lab response tests proving the assessment and remediation sprint adapt.
- Lab-response safety tests for exam dumps, unsafe cyber prompts, fake secrets, real-looking PII, and invalid option references.
- Fake Foundry client tests proving model-backed agents still return raw JSON strings and parse through Pydantic.
- Foundry repair/fallback tests for invalid model JSON, failed repair, and auth/client exceptions.
- Registry tests proving only the selected reasoning agents are model-backed in Foundry mode.
- Adapter tests proving the Foundry project OpenAI-compatible client receives the expected model deployment and response schema.

## Demo Acceptance Evidence

- The Streamlit demo starts locally from `scripts/run_demo.ps1`.
- The app serves HTTP 200 on `http://127.0.0.1:8501`.
- The trace drawer exposes realistic latency values, guardrail verdicts, citations, raw JSON responses, and parsed schema outputs.
- The lab tab supports demo answers and custom learner responses, and the trace records selected lab, lab score, and adaptive remediation reason.
- In Foundry mode, the trace also exposes model mode, deployment name, request id, token usage when available, and fallback reasons.
- In Foundry IQ mode, the trace exposes retrieval provider, knowledge base name, source count, partial-content status, activity summaries when present, and local fallback reasons.

## Known Phase 5 Boundary

Phase 5 can call a configured Foundry IQ-compatible Azure AI Search knowledge base, but live acceptance is manual because CI must remain credential-free. It does not claim direct raw index search, hosted Agent Framework, Foundry evaluations, or production observability integration yet.
