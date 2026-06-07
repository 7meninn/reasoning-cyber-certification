# Cybersecurity Certification Readiness Agent

[![Tests](https://github.com/7meninn/reasoning-cyber-certification/actions/workflows/tests.yml/badge.svg)](https://github.com/7meninn/reasoning-cyber-certification/actions/workflows/tests.yml)

Multi-agent SOC readiness demo for the Agents League Reasoning track.

Phase 6 adds local evaluation evidence and Foundry-compatible eval export while preserving the deterministic local demo. By default the app runs in `mock` mode with `local_mock` retrieval and no Azure credentials. `APP_MODE=foundry` enables model-backed reasoning, and `APP_MODE=foundry_iq` keeps those model-backed agents while retrieving evidence from a Foundry IQ / Azure AI Search knowledge base.

## Demo Story

Synthetic learner `L-1001` is a helpdesk analyst who wants to become a SOC analyst in 4 weeks while working a meeting-heavy schedule. The system recommends a Security+ foundation plus SC-200-oriented readiness path, builds a capacity-aware study plan, runs an interactive SOC lab, scores the attempt, adapts remediation, and shows manager-level readiness insight.

## What Works Now

- Streamlit demo app with learner, path, skill gap, study plan, interactive lab, assessment, manager, and trace views.
- Four synthetic defensive labs: suspicious sign-in, phishing triage, vulnerability prioritization, and KQL interpretation.
- Deterministic lab scoring that maps mistakes to certification-readiness domains and adapts remediation.
- Deterministic mock agents that return raw JSON strings.
- Pydantic validation for every agent handoff, using the same parsing path intended for later LLM responses.
- Explicit workflow state, route branches, agent registry, schema repair, and safe fallback behavior.
- Optional `APP_MODE=foundry` execution for model-backed certification path, gap, plan, assessment, and manager-insight agents.
- Optional `APP_MODE=foundry_iq` execution with live knowledge-base retrieval and explicit `local_mock` fallback.
- Foundry calls isolated behind one adapter using Microsoft Entra ID and a Foundry project endpoint.
- Foundry IQ retrieval isolated behind one adapter using Microsoft Entra ID and Azure AI Search knowledge base APIs.
- Synthetic data only: learners, teams, work signals, knowledge summaries, and SOC lab artifacts.
- Local mock retrieval adapter with explicit `retrieval_mode = local_mock`.
- Reset Demo button in the sidebar.
- Deterministic local evaluation runner with 25 synthetic cases and a committed judge-facing report.
- Foundry-compatible JSONL evaluation export for optional cloud evaluation.
- Agent Trace expander with raw JSON responses, parsed outputs, citations, guardrail verdicts, model metadata, repair/fallback metadata, and realistic latency values.

## Judging Alignment

| Criterion | Evidence in this repo |
|---|---|
| Accuracy and relevance | SOC Analyst readiness flow with cited Security+ and SC-200-oriented recommendations, optionally grounded through Foundry IQ |
| Reasoning | Routed multi-agent path -> gap -> plan -> lab -> assessment -> remediation workflow |
| Creativity | Cybersecurity readiness command center with interactive SOC labs |
| UX and presentation | Streamlit demo, reset button, learner and manager views, visible trace drawer, mode badges |
| Reliability and safety | Pydantic validation, tests, eval report, guardrails, synthetic-only data, Foundry/Foundry IQ fallback |

## Run The Demo

```powershell
git clone https://github.com/7meninn/reasoning-cyber-certification.git
cd reasoning-cyber-certification
.\scripts\run_demo.ps1
```

Open the Streamlit URL printed by the script, usually:

```text
http://127.0.0.1:8501
```

For a background launch:

```powershell
.\scripts\run_demo.ps1 -Background
```

## Optional Foundry Mode

Mock mode is the recommended submission-safe default. To try model-backed agents locally, sign in with Azure CLI, set the Foundry project endpoint and model deployment, then run the demo:

```powershell
az login
$env:APP_MODE="foundry"
$env:AZURE_AI_PROJECT_ENDPOINT="https://<resource>.services.ai.azure.com/api/projects/<project>"
$env:AZURE_AI_MODEL_DEPLOYMENT="<deployment-name>"
.\scripts\run_demo.ps1
```

If Foundry config or credentials are missing, the app falls back to deterministic mock mode and records the fallback reason in the trace.

## Optional Foundry IQ Mode

To try live grounding, create a Foundry IQ-compatible Azure AI Search knowledge base from the synthetic sources in `data/synthetic/knowledge_docs/sources.json`, then run:

```powershell
az login
$env:APP_MODE="foundry_iq"
$env:AZURE_AI_PROJECT_ENDPOINT="https://<resource>.services.ai.azure.com/api/projects/<project>"
$env:AZURE_AI_MODEL_DEPLOYMENT="<deployment-name>"
$env:AZURE_AI_SEARCH_ENDPOINT="https://<search-service>.search.windows.net"
$env:FOUNDRY_IQ_KNOWLEDGE_BASE="<knowledge-base-name>"
.\scripts\run_demo.ps1
```

Successful live retrieval is labeled `retrieval_mode = foundry_iq`. Any retrieval failure falls back visibly to `local_mock` while preserving the demo flow.

## Run Tests

```powershell
.\scripts\run_tests.ps1
```

The test runner installs only backend test dependencies. The demo runner installs Streamlit.

Current local result:

```text
65 passed
```

## Run Evaluation

```powershell
.\scripts\run_eval.ps1
```

Current local evaluation result:

| Metric | Value | Threshold | Result |
|---|---:|---:|---|
| route_accuracy | 100% | 100% | PASS |
| task_adherence | 100% | 100% | PASS |
| safety_pass_rate | 100% | 100% | PASS |
| citation_coverage | 100% | 100% | PASS |
| grounded_citation_support | 100% | 100% | PASS |
| manager_privacy_pass_rate | 100% | 100% | PASS |
| capacity_fit_pass_rate | 100% | 100% | PASS |
| lab_assessment_correctness | 100% | 100% | PASS |
| fallback_success | 100% | 100% | PASS |
| average_trace_latency_ms | 7403.36 ms | 11000 ms | PASS |
| p95_trace_latency_ms | 9908.00 ms | 11000 ms | PASS |

See `docs/evaluation-report.md` for the committed report and `docs/foundry-evaluation.md` for optional Foundry evaluation instructions.

## Phase 6 Design Notes

Mock agents intentionally return exact JSON strings, not Python dictionaries. The workflow parses those strings through Pydantic models before using the outputs. This proves schema validation, parsing errors, and trace capture before real LLM calls are introduced.

Foundry-backed agents use the same executor contract: raw JSON string first, then Pydantic validation, repair attempt, and safe fallback. Foundry IQ retrieval is also adapter-based: live knowledge-base results become an `EvidenceBundle`; missing, malformed, unauthorized, empty, or timed-out retrieval falls back to `local_mock` and records the reason in `RunTrace`.

Lab generation and lab scoring remain deterministic in all modes for demo reliability. The assessment agent consumes the parsed `LabAttempt`, so custom learner answers visibly change the readiness result and remediation sprint without depending on a live model call.

The local evaluation runner executes deterministic `mock` mode only by default. It measures route accuracy, task adherence, safety, citation coverage, grounded citation support, manager privacy, capacity fit, lab assessment correctness, fallback success, and trace latency. It does not make live Azure or Foundry calls.

## Repository Map

```text
app/                         Streamlit app, schemas, mock agents, orchestration, tests, eval cases
data/synthetic/              Synthetic learners, teams, knowledge docs, and scenario labs
docs/                        Architecture, data safety, demo script, evaluation notes
scripts/                     One-command demo and test runners
```

## Trace Screenshot Placeholder

The `Agent Trace` expander is available in the running Streamlit app and shows raw JSON responses, parsed outputs, lab score, selected lab, adaptive remediation reason, citations, guardrail verdicts, model metadata, retrieval provider, knowledge base name, repair/fallback metadata, route, fallback mode, and latency. Screenshots can be added after submission without changing the runnable demo.

## Synthetic Data Statement

All included learners, teams, logs, users, IP addresses, work signals, and incident artifacts are synthetic demo content. The repository must not contain real customer data, employee records, tenant content, credentials, secrets, real exam questions, or confidential material.

## License

MIT
