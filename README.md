# Cybersecurity Certification Readiness Agent

[![Tests](https://github.com/7meninn/reasoning-cyber-certification/actions/workflows/tests.yml/badge.svg)](https://github.com/7meninn/reasoning-cyber-certification/actions/workflows/tests.yml)

Multi-agent SOC readiness demo for the Agents League Reasoning track.

Phase 2 implements a deterministic local multi-agent orchestration skeleton for the Agents League Reasoning track. It runs a SOC Analyst readiness demo in `local_mock` mode with no Azure, Foundry, or Foundry IQ credentials.

## Demo Story

Synthetic learner `L-1001` is a helpdesk analyst who wants to become a SOC analyst in 4 weeks while working a meeting-heavy schedule. The system recommends a Security+ foundation plus SC-200-oriented readiness path, builds a capacity-aware study plan, runs a suspicious sign-in lab, returns a CONDITIONAL readiness verdict, and shows manager-level readiness insight.

## What Works Now

- Streamlit demo app with learner, path, skill gap, study plan, lab, assessment, manager, and trace views.
- Deterministic mock agents that return raw JSON strings.
- Pydantic validation for every agent handoff, using the same parsing path intended for later LLM responses.
- Explicit workflow state, route branches, agent registry, schema repair, and safe fallback behavior.
- Synthetic data only: learners, teams, work signals, knowledge summaries, and SOC lab artifacts.
- Local mock retrieval adapter with explicit `retrieval_mode = local_mock`.
- Reset Demo button in the sidebar.
- Agent Trace expander with raw JSON responses, parsed outputs, citations, guardrail verdicts, repair/fallback metadata, and realistic latency values.

## Judging Alignment

| Criterion | Evidence in this repo |
|---|---|
| Accuracy and relevance | SOC Analyst readiness flow with cited Security+ and SC-200-oriented recommendations |
| Reasoning | Routed multi-agent path -> gap -> plan -> lab -> assessment -> remediation workflow |
| Creativity | Cybersecurity readiness command center with a suspicious sign-in lab |
| UX and presentation | Streamlit demo, reset button, learner and manager views, visible trace drawer |
| Reliability and safety | Pydantic validation, tests, guardrails, synthetic-only data, local fallback mode |

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

## Run Tests

```powershell
.\scripts\run_tests.ps1
```

The test runner installs only backend test dependencies. The demo runner installs Streamlit.

Current local result:

```text
19 passed
```

## Phase 2 Design Notes

Mock agents intentionally return exact JSON strings, not Python dictionaries. The workflow parses those strings through Pydantic models before using the outputs. This proves schema validation, parsing errors, and trace capture before real LLM calls are introduced.

The app is honest about grounding: Phase 2 uses local mock retrieval and does not claim live Foundry IQ integration. Later phases can replace the retrieval adapter and mock agent raw JSON source without changing the workflow contracts.

## Repository Map

```text
app/                         Streamlit app, schemas, mock agents, orchestration, tests
data/synthetic/              Synthetic learners, teams, knowledge docs, and lab artifacts
docs/                        Architecture, data safety, demo script, evaluation notes
scripts/                     One-command demo and test runners
```

## Trace Screenshot Placeholder

The `Agent Trace` expander is available in the running Streamlit app and shows raw JSON responses, parsed outputs, citations, guardrail verdicts, repair/fallback metadata, route, fallback mode, and latency. Screenshots can be added after submission without changing the runnable demo.

## Synthetic Data Statement

All included learners, teams, logs, users, IP addresses, work signals, and incident artifacts are synthetic demo content. The repository must not contain real customer data, employee records, tenant content, credentials, secrets, real exam questions, or confidential material.

## License

MIT
