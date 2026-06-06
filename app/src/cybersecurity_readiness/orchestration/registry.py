from __future__ import annotations

from ..agents import (
    MockAssessmentAgent,
    MockCertificationPathAdvisorAgent,
    MockIntakeRouterAgent,
    MockKnowledgeCuratorAgent,
    MockLabScoringAgent,
    MockManagerInsightsAgent,
    MockSafetyRefusalAgent,
    MockScenarioLabCoachAgent,
    MockSkillGapAnalystAgent,
    MockStudyPlanGeneratorAgent,
    MockVerifierSafetyAgent,
)
from ..config import RuntimeConfig
from ..foundry.agents import FoundryBackedAgent, JsonModelClient
from ..foundry.client import FoundryModelClient
from .executor import AgentExecutor


def build_mock_agent_registry() -> dict[str, AgentExecutor]:
    return {
        "intake_router": AgentExecutor(MockIntakeRouterAgent()),
        "knowledge_curator": AgentExecutor(MockKnowledgeCuratorAgent()),
        "certification_path_advisor": AgentExecutor(MockCertificationPathAdvisorAgent()),
        "skill_gap_analyst": AgentExecutor(MockSkillGapAnalystAgent()),
        "study_plan_generator": AgentExecutor(MockStudyPlanGeneratorAgent()),
        "scenario_lab_coach": AgentExecutor(MockScenarioLabCoachAgent()),
        "lab_scoring": AgentExecutor(MockLabScoringAgent()),
        "assessment": AgentExecutor(MockAssessmentAgent()),
        "manager_insights": AgentExecutor(MockManagerInsightsAgent()),
        "verifier_safety": AgentExecutor(MockVerifierSafetyAgent()),
        "safety_refusal": AgentExecutor(MockSafetyRefusalAgent()),
    }


def build_foundry_agent_registry(
    config: RuntimeConfig,
    model_client: JsonModelClient | None = None,
) -> dict[str, AgentExecutor]:
    client = model_client or FoundryModelClient(config)
    registry = build_mock_agent_registry()

    foundry_agents = {
        "certification_path_advisor": FoundryBackedAgent(
            "certification_path_advisor",
            MockCertificationPathAdvisorAgent(),
            client,
        ),
        "skill_gap_analyst": FoundryBackedAgent(
            "skill_gap_analyst",
            MockSkillGapAnalystAgent(),
            client,
        ),
        "study_plan_generator": FoundryBackedAgent(
            "study_plan_generator",
            MockStudyPlanGeneratorAgent(),
            client,
        ),
        "assessment": FoundryBackedAgent(
            "assessment",
            MockAssessmentAgent(),
            client,
        ),
        "manager_insights": FoundryBackedAgent(
            "manager_insights",
            MockManagerInsightsAgent(),
            client,
        ),
    }

    for key, agent in foundry_agents.items():
        registry[key] = AgentExecutor(agent, repair_json=agent.repair_response)

    return registry
