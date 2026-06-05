# Phase 2 Architecture

The Phase 2 app is a deterministic local multi-agent workflow:

1. Streamlit collects the selected synthetic learner and demo request.
2. `run_demo_workflow` delegates to `OrchestratedWorkflowRunner`.
3. The runner creates `WorkflowState`, evaluates input safety, and executes the Intake Router.
4. The route chooses one branch: SOC learner flow, manager insight flow, or safety refusal flow.
5. `AgentExecutor` invokes each registered mock agent, parses raw JSON through Pydantic, records trace steps, and performs one repair/fallback cycle on invalid output.
6. `LocalMockRetrievalAdapter` returns validated evidence in `local_mock` mode where the route needs grounding.
7. Streamlit renders the selected route and exposes `RunTrace` with raw JSON, parsed output, citations, guardrail verdicts, repair/fallback metadata, route, fallback mode, and latency.

Phase 2 does not call Foundry, Foundry IQ, Azure AI Search, or the `agent-framework` package yet. It uses Agent Framework-style workflow concepts locally so later phases can replace mock agent execution with model-backed agents while preserving typed contracts.
