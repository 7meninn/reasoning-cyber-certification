# Phase 3 Architecture

The Phase 3 app is a local multi-agent workflow with two execution modes:

- `mock`: deterministic default mode with no cloud credentials.
- `foundry`: optional model-backed mode for selected reasoning agents.

1. Streamlit collects the selected synthetic learner and demo request.
2. `run_demo_workflow` loads runtime config and delegates to `OrchestratedWorkflowRunner`.
3. The runner creates `WorkflowState`, evaluates input safety, and executes the Intake Router.
4. The route chooses one branch: SOC learner flow, manager insight flow, or safety refusal flow.
5. `AgentExecutor` invokes each registered agent, parses raw JSON through Pydantic, records trace steps, and performs one repair/fallback cycle on invalid output.
6. `LocalMockRetrievalAdapter` returns validated evidence in `local_mock` mode where the route needs grounding.
7. Streamlit renders the selected route and exposes `RunTrace` with raw JSON, parsed output, citations, guardrail verdicts, model metadata, repair/fallback metadata, route, fallback mode, and latency.

In `foundry` mode, Certification Path Advisor, Skill Gap Analyst, Study Plan Generator, Assessment, and Manager Insights use `FoundryBackedAgent`. The router, safety refusal, knowledge curator, and scenario lab remain deterministic for reliability and safety. Foundry calls are isolated behind `FoundryModelClient`, which uses Microsoft Entra ID and a Foundry project endpoint to obtain an OpenAI-compatible client.

Phase 3 still does not call Foundry IQ, Azure AI Search, hosted Agent Framework, or production observability services. Retrieval remains explicitly `local_mock`.
