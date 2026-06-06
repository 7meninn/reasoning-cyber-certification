import json

from cybersecurity_readiness.safety import plan_fits_capacity
from cybersecurity_readiness.config import load_runtime_config
from cybersecurity_readiness.orchestration.registry import build_mock_agent_registry
from cybersecurity_readiness.orchestration.runner import OrchestratedWorkflowRunner
from cybersecurity_readiness.retrieval import FoundryIqRetrievalAdapter, KnowledgeBaseRetrieveResponse
from cybersecurity_readiness.workflow import run_demo_workflow


def test_golden_path_l1001_runs_end_to_end_in_local_mock_mode():
    result = run_demo_workflow("L-1001")

    assert result.learner.learner_id == "L-1001"
    assert result.route.route == "soc_readiness_demo"
    assert result.evidence.retrieval_mode == "local_mock"
    assert result.certification_path.target_role == "SOC Analyst"
    assert "Microsoft SC-200-oriented SOC readiness" in result.certification_path.recommended_certifications
    assert result.study_plan.duration_weeks == 4
    assert result.scenario_lab.lab_id == "LAB-SOC-001"
    assert result.lab_attempt.lab_id == "LAB-SOC-001"
    assert result.lab_attempt.readiness == "CONDITIONAL"
    assert result.assessment_result.overall_readiness == "CONDITIONAL"
    assert result.manager_insight.team_id == "TEAM-SOC-A"


def test_trace_contains_raw_json_guardrails_citations_and_realistic_latency():
    result = run_demo_workflow("L-1001")
    trace = result.trace

    assert trace.retrieval_mode == "local_mock"
    assert trace.fallback_mode is True
    assert trace.latency_ms == 9908
    assert len(trace.tool_calls) == 1
    assert trace.tool_calls[0].tool_name == "retrieve_evidence"
    assert len(trace.agent_steps) == 10
    assert trace.selected_lab_id == "LAB-SOC-001"
    assert trace.lab_score == 60
    assert trace.lab_readiness == "CONDITIONAL"
    assert all(isinstance(step.raw_json_response, str) for step in trace.agent_steps)
    assert any(verdict.verdict == "allowed" for verdict in trace.guardrail_verdicts)
    assert {"OFFICIAL-SC200", "SYN-SOC-GUIDE", "SYN-SIGNIN-LAB"} <= {
        citation.source_id for citation in trace.citations
    }


def test_study_plan_fits_l1001_capacity():
    result = run_demo_workflow("L-1001")

    assert plan_fits_capacity(result.study_plan)


def test_foundry_mode_missing_config_falls_back_to_mock_trace():
    config = load_runtime_config({"APP_MODE": "foundry"})

    result = run_demo_workflow("L-1001", config=config)

    assert result.trace.requested_app_mode == "foundry"
    assert result.trace.model_mode == "mock"
    assert result.trace.mode_fallback_reason is not None
    assert result.assessment_result.overall_readiness == "CONDITIONAL"


class FakeKnowledgeBaseClient:
    def retrieve(self, **kwargs):
        del kwargs
        docs = [
            {
                "ref_id": "OFFICIAL-SC200",
                "title": "Microsoft SC-200 certification overview",
                "content": "SC-200 focuses on Microsoft security operations analysis.",
                "url": "https://learn.microsoft.com/en-us/credentials/certifications/security-operations-analyst/",
            },
            {
                "ref_id": "OFFICIAL-SECURITYPLUS",
                "title": "CompTIA Security+ public certification page",
                "content": "Security+ covers broad cybersecurity foundation concepts.",
                "url": "https://www.comptia.org/en/certifications/security/",
            },
            {
                "ref_id": "SYN-SOC-GUIDE",
                "title": "Synthetic SOC Analyst Enablement Guide",
                "content": "Synthetic SOC readiness covers alert triage, KQL, and reporting.",
            },
            {
                "ref_id": "SYN-WORK-CAPACITY",
                "title": "Synthetic Team Learning Capacity Report",
                "content": "Synthetic capacity reports constrain learning plans around focus hours.",
            },
            {
                "ref_id": "SYN-MANAGER-BRIEF",
                "title": "Synthetic Manager Readiness Dashboard Brief",
                "content": "Manager summaries aggregate readiness without private learner weaknesses.",
            },
        ]
        return KnowledgeBaseRetrieveResponse(
            status_code=200,
            payload={
                "response": [
                    {
                        "role": "assistant",
                        "content": [{"type": "text", "text": json.dumps(docs)}],
                    }
                ],
                "activity": [{"type": "searchIndex", "count": len(docs), "elapsedMs": 45}],
            },
            latency_ms=321,
        )


def test_foundry_iq_golden_path_uses_live_retrieval_adapter_metadata():
    config = load_runtime_config(
        {
            "APP_MODE": "foundry_iq",
            "AZURE_AI_PROJECT_ENDPOINT": "https://demo.services.ai.azure.com/api/projects/readiness",
            "AZURE_AI_MODEL_DEPLOYMENT": "gpt-4o-mini",
            "AZURE_AI_SEARCH_ENDPOINT": "https://demo.search.windows.net",
            "FOUNDRY_IQ_KNOWLEDGE_BASE": "soc-readiness-kb",
        }
    )
    adapter = FoundryIqRetrievalAdapter(config, retrieval_client=FakeKnowledgeBaseClient())
    runner = OrchestratedWorkflowRunner(
        config=config,
        registry=build_mock_agent_registry(),
        retrieval_adapter=adapter,
    )

    result = runner.run("L-1001")

    assert result.route.route == "soc_readiness_demo"
    assert result.evidence.retrieval_mode == "foundry_iq"
    assert result.trace.requested_app_mode == "foundry_iq"
    assert result.trace.effective_app_mode == "foundry_iq"
    assert result.trace.model_mode == "foundry"
    assert result.trace.retrieval_mode == "foundry_iq"
    assert result.trace.knowledge_base_name == "soc-readiness-kb"
    assert result.trace.tool_calls[0].retrieval_provider == "foundry_iq"
    assert result.trace.tool_calls[0].source_count == 5
    assert result.assessment_result.overall_readiness == "CONDITIONAL"
