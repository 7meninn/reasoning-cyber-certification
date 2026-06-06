import json

import pytest

from cybersecurity_readiness.agents import (
    MockAssessmentAgent,
    MockCertificationPathAdvisorAgent,
    MockIntakeRouterAgent,
    MockKnowledgeCuratorAgent,
    MockLabScoringAgent,
    MockManagerInsightsAgent,
    MockScenarioLabCoachAgent,
    MockSkillGapAnalystAgent,
    MockStudyPlanGeneratorAgent,
    MockVerifierSafetyAgent,
    parse_agent_json,
)
from cybersecurity_readiness.schemas import RouteDecision, RunTrace


AGENTS = [
    MockIntakeRouterAgent(),
    MockKnowledgeCuratorAgent(),
    MockCertificationPathAdvisorAgent(),
    MockSkillGapAnalystAgent(),
    MockStudyPlanGeneratorAgent(),
    MockScenarioLabCoachAgent(),
    MockLabScoringAgent(),
    MockAssessmentAgent(),
    MockManagerInsightsAgent(),
    MockVerifierSafetyAgent(),
]


def test_mock_agents_return_raw_json_strings_and_parse_through_schema():
    trace = RunTrace(run_id="TEST-RUN", route="pending")

    for agent in AGENTS:
        raw = agent.raw_response()

        assert isinstance(raw, str)
        assert isinstance(json.loads(raw), dict)

        parsed = parse_agent_json(raw, agent.output_schema)
        assert isinstance(parsed, agent.output_schema)

        result = agent.run(trace=trace, input_summary="test")
        assert isinstance(result.raw_json, str)
        assert result.raw_json.strip().startswith("{")
        assert result.parsed == parsed

    assert len(trace.agent_steps) == len(AGENTS)
    assert all(isinstance(step.raw_json_response, str) for step in trace.agent_steps)


def test_parse_agent_json_rejects_python_dict_bypass():
    with pytest.raises(TypeError, match="raw JSON strings"):
        parse_agent_json({"route": "soc_readiness_demo"}, RouteDecision)  # type: ignore[arg-type]
