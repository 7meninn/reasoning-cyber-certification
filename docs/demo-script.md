# Five-Minute Demo Script

1. Start the app with `.\scripts\run_demo.ps1`.
2. Confirm `L-1001`, the suspicious sign-in lab, and `conditional` demo answers are selected.
3. Confirm the sidebar shows `Execution: mock` and `Retrieval: local_mock` unless you intentionally configured Foundry or Foundry IQ.
4. Click `Run Demo` and start on the judge snapshot: learner, readiness, lab score, mode, retrieval, eval status, citations, and latency.
5. Open Path and show Security+ foundation plus SC-200-oriented readiness.
6. Open Skill Gaps and call out incident response, KQL, and alert triage.
7. Open Study Plan and show the 4-week capacity-aware schedule.
8. Open Scenario Lab and review the synthetic artifacts, questions, score debrief, rubric, and `Use Demo Answers` path.
9. Submit one custom answer or switch the sidebar answer profile to show scoring/remediation changes.
10. Open Assessment and show the adaptive verdict plus remediation sprint.
11. Open Manager and show aggregate readiness, capacity risk, and privacy note.
12. Open Evaluation and show the committed local eval metrics.
13. Open Agent Trace and show the trace summary, execution order, guardrails, citations, fallback labels, and raw JSON.
14. Click Reset Demo before rehearsing another run.

For a Foundry IQ rehearsal, configure `APP_MODE=foundry_iq`, confirm the sidebar shows the knowledge base name, and call out whether the trace says `retrieval_mode = foundry_iq` or an explicit `local_mock` fallback.

Before recording or submitting, run:

```powershell
.\scripts\run_tests.ps1
.\scripts\run_eval.ps1
```
