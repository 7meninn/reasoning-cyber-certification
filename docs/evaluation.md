# Evaluation

## Current Phase 1 Evidence

The Phase 1 implementation is deterministic by design. It validates the core contracts and safety posture before real Foundry or LLM calls are introduced.

Current local test result:

```text
13 passed
```

## What The Tests Cover

- Pydantic schema validation for typed agent handoffs.
- Deterministic mock agents returning raw JSON strings before parsing.
- A guard test that fails if a mock agent bypasses JSON parsing with a Python dictionary.
- Local mock retrieval with explicit `retrieval_mode = local_mock`.
- Citation presence and citation shape validation.
- Safety checks for exam dumps, unsafe cyber intent, secret-like strings, and real-looking PII.
- Golden path for learner `L-1001`: route, evidence, path, gaps, plan, lab, assessment, manager insight, and trace.

## Demo Acceptance Evidence

- The Streamlit demo starts locally from `scripts/run_demo.ps1`.
- The app serves HTTP 200 on `http://127.0.0.1:8501`.
- The trace drawer exposes realistic latency values, guardrail verdicts, citations, raw JSON responses, and parsed schema outputs.

## Known Phase 1 Boundary

Phase 1 runs in `local_mock` mode. It does not claim live Foundry, Foundry IQ, Azure AI Search, or Microsoft Agent Framework integration yet. Later phases can replace the deterministic adapters while preserving the same typed contracts.

