# Phase 1 Architecture

The Phase 1 app is a deterministic local demo path:

1. Streamlit collects the selected synthetic learner and demo request.
2. `run_demo_workflow` creates a `RunTrace` and evaluates input safety.
3. `LocalMockRetrievalAdapter` returns a validated `EvidenceBundle` in `local_mock` mode.
4. Mock agents return raw JSON strings.
5. Pydantic parses each raw JSON string into a typed schema.
6. The workflow records raw JSON, parsed output, citations, guardrail verdicts, fallback mode, and latency in `RunTrace`.
7. Streamlit renders learner, path, skill gap, plan, lab, assessment, manager, and trace views.

Phase 1 does not call Foundry, Foundry IQ, Azure AI Search, or Microsoft Agent Framework orchestration. Those integrations should replace adapters and agent execution sources in later phases while preserving the typed contracts.

