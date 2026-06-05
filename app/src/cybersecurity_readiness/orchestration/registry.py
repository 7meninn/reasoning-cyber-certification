from __future__ import annotations

from ..agents import (
    MockAssessmentAgent,
    MockCertificationPathAdvisorAgent,
    MockIntakeRouterAgent,
    MockKnowledgeCuratorAgent,
    MockManagerInsightsAgent,
    MockSafetyRefusalAgent,
    MockScenarioLabCoachAgent,
    MockSkillGapAnalystAgent,
    MockStudyPlanGeneratorAgent,
    MockVerifierSafetyAgent,
)
from .executor import AgentExecutor


def build_mock_agent_registry() -> dict[str, AgentExecutor]:
    return {
        "intake_router": AgentExecutor(MockIntakeRouterAgent()),
        "knowledge_curator": AgentExecutor(MockKnowledgeCuratorAgent()),
        "certification_path_advisor": AgentExecutor(MockCertificationPathAdvisorAgent()),
        "skill_gap_analyst": AgentExecutor(MockSkillGapAnalystAgent()),
        "study_plan_generator": AgentExecutor(MockStudyPlanGeneratorAgent()),
        "scenario_lab_coach": AgentExecutor(MockScenarioLabCoachAgent()),
        "assessment": AgentExecutor(MockAssessmentAgent()),
        "manager_insights": AgentExecutor(MockManagerInsightsAgent()),
        "verifier_safety": AgentExecutor(MockVerifierSafetyAgent()),
        "safety_refusal": AgentExecutor(MockSafetyRefusalAgent()),
    }

