from cybersecurity_readiness.safety import plan_fits_capacity
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
    assert result.assessment_result.overall_readiness == "CONDITIONAL"
    assert result.manager_insight.team_id == "TEAM-SOC-A"


def test_trace_contains_raw_json_guardrails_citations_and_realistic_latency():
    result = run_demo_workflow("L-1001")
    trace = result.trace

    assert trace.retrieval_mode == "local_mock"
    assert trace.fallback_mode is True
    assert trace.latency_ms == 9175
    assert len(trace.tool_calls) == 1
    assert trace.tool_calls[0].tool_name == "retrieve_evidence"
    assert len(trace.agent_steps) == 9
    assert all(isinstance(step.raw_json_response, str) for step in trace.agent_steps)
    assert any(verdict.verdict == "allowed" for verdict in trace.guardrail_verdicts)
    assert {"OFFICIAL-SC200", "SYN-SOC-GUIDE", "SYN-SIGNIN-LAB"} <= {
        citation.source_id for citation in trace.citations
    }


def test_study_plan_fits_l1001_capacity():
    result = run_demo_workflow("L-1001")

    assert plan_fits_capacity(result.study_plan)

