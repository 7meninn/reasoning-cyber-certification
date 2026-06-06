# Evaluation

## Current Phase 3 Evidence

The Phase 3 implementation keeps deterministic mock mode as the default and adds optional Foundry-backed model agents behind fake-client-tested adapters. CI does not make live Azure calls.

Current local test result:

```text
31 passed
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
- Fake Foundry client tests proving model-backed agents still return raw JSON strings and parse through Pydantic.
- Foundry repair/fallback tests for invalid model JSON, failed repair, and auth/client exceptions.
- Registry tests proving only the selected reasoning agents are model-backed in Foundry mode.
- Adapter tests proving the Foundry project OpenAI-compatible client receives the expected model deployment and response schema.

## Demo Acceptance Evidence

- The Streamlit demo starts locally from `scripts/run_demo.ps1`.
- The app serves HTTP 200 on `http://127.0.0.1:8501`.
- The trace drawer exposes realistic latency values, guardrail verdicts, citations, raw JSON responses, and parsed schema outputs.
- In Foundry mode, the trace also exposes model mode, deployment name, request id, token usage when available, and fallback reasons.

## Known Phase 3 Boundary

Phase 3 can call a configured Foundry model deployment, but retrieval remains `local_mock`. It does not claim Foundry IQ, Azure AI Search, hosted Agent Framework, or production observability integration yet. Live Foundry acceptance is manual because CI must remain credential-free.
