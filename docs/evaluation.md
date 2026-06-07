# Evaluation

## Current Submission Evidence

The submission keeps deterministic mock mode as the default, preserves optional Foundry-backed model agents and optional Foundry IQ retrieval, and includes a local evaluation runner with a committed report. CI does not make live Azure calls.

Current local test result:

```text
65 passed
```

Current local evaluation result:

```text
25 eval cases, PASS
route_accuracy: 100%
task_adherence: 100%
safety_pass_rate: 100%
citation_coverage: 100%
grounded_citation_support: 100%
average_trace_latency_ms: 7403.36 ms
p95_trace_latency_ms: 9908 ms
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
- Eval dataset validation for 25 synthetic cases across learner, manager, lab, retrieval/citation, fallback, and safety categories.
- Local eval runner tests proving deterministic metrics, threshold failure behavior, Markdown report content, and sanitized Foundry export.

## Demo Acceptance Evidence

- The Streamlit demo starts locally from `scripts/run_demo.ps1`.
- The app serves HTTP 200 on `http://127.0.0.1:8501`.
- The trace drawer exposes realistic latency values, guardrail verdicts, citations, raw JSON responses, and parsed schema outputs.
- The lab tab supports demo answers and custom learner responses, and the trace records selected lab, lab score, and adaptive remediation reason.
- In Foundry mode, the trace also exposes model mode, deployment name, request id, token usage when available, and fallback reasons.
- In Foundry IQ mode, the trace exposes retrieval provider, knowledge base name, source count, partial-content status, activity summaries when present, and local fallback reasons.
- `scripts/run_eval.ps1` produces a local report and Foundry-compatible JSONL export without cloud calls.
- `docs/evaluation-report.md` contains the committed judge-facing evaluation evidence.

## Known Submission Boundary

The app can call a configured Foundry IQ-compatible Azure AI Search knowledge base during manual demo runs, but live acceptance is manual because CI must remain credential-free. It does not claim direct raw index search, hosted Agent Framework deployment, live Foundry evaluation execution in CI, or production observability integration yet.
