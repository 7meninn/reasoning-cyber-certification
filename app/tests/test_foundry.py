from typing import Any

from cybersecurity_readiness.agents import (
    MockCertificationPathAdvisorAgent,
    MockManagerInsightsAgent,
)
from cybersecurity_readiness.config import load_runtime_config
from cybersecurity_readiness.foundry.agents import FoundryBackedAgent
from cybersecurity_readiness.foundry.client import FoundryModelClient, ModelJsonResponse
from cybersecurity_readiness.loader import get_learner
from cybersecurity_readiness.orchestration.executor import AgentExecutor
from cybersecurity_readiness.orchestration.registry import build_foundry_agent_registry
from cybersecurity_readiness.orchestration.state import WorkflowState
from cybersecurity_readiness.schemas import CertificationPath, ManagerInsight, RunTrace


def make_foundry_config():
    return load_runtime_config(
        {
            "APP_MODE": "foundry",
            "AZURE_AI_PROJECT_ENDPOINT": "https://demo.services.ai.azure.com/api/projects/readiness",
            "AZURE_AI_MODEL_DEPLOYMENT": "gpt-4o-mini",
        }
    )


def make_state() -> WorkflowState:
    return WorkflowState(
        request_text="Prepare L-1001 for SOC readiness.",
        learner=get_learner("L-1001"),
        trace=RunTrace(
            run_id="TEST-FOUNDRY",
            route="soc_readiness_demo",
            requested_app_mode="foundry",
            model_mode="foundry",
            model_deployment="gpt-4o-mini",
        ),
    )


class FakeJsonModelClient:
    def __init__(
        self,
        responses: list[str | Exception] | None = None,
        error: Exception | None = None,
    ) -> None:
        self.responses = responses or []
        self.error = error
        self.calls: list[dict[str, Any]] = []

    def generate_json(
        self,
        *,
        agent_name: str,
        system_prompt: str,
        user_payload: dict[str, Any],
        output_schema: type,
    ) -> ModelJsonResponse:
        self.calls.append(
            {
                "agent_name": agent_name,
                "system_prompt": system_prompt,
                "user_payload": user_payload,
                "output_schema": output_schema,
            }
        )
        if self.error is not None:
            raise self.error
        next_response = self.responses.pop(0)
        if isinstance(next_response, Exception):
            raise next_response
        return ModelJsonResponse(
            raw_json=next_response,
            latency_ms=222,
            request_id=f"req-{len(self.calls)}",
            model_deployment="gpt-4o-mini",
            token_usage={"prompt_tokens": 12, "completion_tokens": 34, "total_tokens": 46},
            finish_reason="stop",
        )


def test_foundry_agent_returns_raw_json_and_parses_through_executor():
    fallback = MockCertificationPathAdvisorAgent()
    fake_client = FakeJsonModelClient([fallback.raw_response()])
    agent = FoundryBackedAgent("certification_path_advisor", fallback, fake_client)
    state = make_state()

    result = AgentExecutor(agent, repair_json=agent.repair_response).execute(
        state,
        "call Foundry certification advisor",
    )

    step = state.trace.agent_steps[0]
    assert isinstance(result.raw_json, str)
    assert isinstance(result.parsed, CertificationPath)
    assert step.status == "success"
    assert step.model_mode == "foundry"
    assert step.model_deployment == "gpt-4o-mini"
    assert step.model_request_id == "req-1"
    assert step.token_usage == {"prompt_tokens": 12, "completion_tokens": 34, "total_tokens": 46}
    assert fake_client.calls[0]["output_schema"] is CertificationPath


def test_invalid_foundry_json_triggers_one_repair_attempt():
    fallback = MockCertificationPathAdvisorAgent()
    fake_client = FakeJsonModelClient(['{"target_role": "SOC Analyst"}', fallback.raw_response()])
    agent = FoundryBackedAgent("certification_path_advisor", fallback, fake_client)
    state = make_state()

    result = AgentExecutor(agent, repair_json=agent.repair_response).execute(
        state,
        "repair invalid Foundry certification advisor output",
    )

    step = state.trace.agent_steps[0]
    assert result.parsed.target_role == "SOC Analyst"
    assert len(fake_client.calls) == 2
    assert step.status == "repaired"
    assert step.repair_attempted is True
    assert step.attempt_count == 2
    assert step.fallback_used is False
    assert "Schema Repair" in fake_client.calls[1]["agent_name"]


def test_failed_foundry_repair_uses_safe_schema_fallback():
    fallback = MockCertificationPathAdvisorAgent()
    fake_client = FakeJsonModelClient(['{"bad": true}', '{"still": "bad"}'])
    agent = FoundryBackedAgent("certification_path_advisor", fallback, fake_client)
    state = make_state()

    result = AgentExecutor(agent, repair_json=agent.repair_response).execute(
        state,
        "fallback invalid Foundry certification advisor output",
    )

    step = state.trace.agent_steps[0]
    assert len(fake_client.calls) == 2
    assert step.status == "fallback"
    assert step.repair_attempted is True
    assert step.fallback_used is True
    assert result.parsed.confidence == 0.1
    assert state.fallback_flags == ["Certification Path Advisor Agent"]


def test_foundry_repair_exception_uses_safe_schema_fallback():
    fallback = MockCertificationPathAdvisorAgent()
    fake_client = FakeJsonModelClient(['{"bad": true}', RuntimeError("repair offline")])
    agent = FoundryBackedAgent("certification_path_advisor", fallback, fake_client)
    state = make_state()

    result = AgentExecutor(agent, repair_json=agent.repair_response).execute(
        state,
        "fallback failed Foundry repair call",
    )

    step = state.trace.agent_steps[0]
    assert len(fake_client.calls) == 2
    assert step.status == "fallback"
    assert step.repair_attempted is True
    assert step.fallback_used is True
    assert "repair offline" in (step.validation_error or "")
    assert result.parsed.confidence == 0.1


def test_foundry_call_exception_falls_back_to_mock_raw_json_and_records_trace():
    fallback = MockCertificationPathAdvisorAgent()
    fake_client = FakeJsonModelClient(error=RuntimeError("credential unavailable"))
    agent = FoundryBackedAgent("certification_path_advisor", fallback, fake_client)
    state = make_state()

    result = AgentExecutor(agent, repair_json=agent.repair_response).execute(
        state,
        "fallback Foundry auth failure",
    )

    step = state.trace.agent_steps[0]
    assert result.parsed.target_role == "SOC Analyst"
    assert step.status == "fallback"
    assert step.fallback_used is True
    assert step.model_mode == "mock"
    assert "credential unavailable" in (step.fallback_reason or "")
    assert state.fallback_flags == ["Certification Path Advisor Agent"]


def test_foundry_registry_only_replaces_selected_reasoning_agents():
    registry = build_foundry_agent_registry(make_foundry_config(), FakeJsonModelClient())

    assert isinstance(registry["certification_path_advisor"].agent, FoundryBackedAgent)
    assert isinstance(registry["skill_gap_analyst"].agent, FoundryBackedAgent)
    assert isinstance(registry["study_plan_generator"].agent, FoundryBackedAgent)
    assert isinstance(registry["assessment"].agent, FoundryBackedAgent)
    assert isinstance(registry["manager_insights"].agent, FoundryBackedAgent)
    assert not isinstance(registry["intake_router"].agent, FoundryBackedAgent)
    assert not isinstance(registry["knowledge_curator"].agent, FoundryBackedAgent)
    assert not isinstance(registry["scenario_lab_coach"].agent, FoundryBackedAgent)
    assert not isinstance(registry["lab_scoring"].agent, FoundryBackedAgent)
    assert not isinstance(registry["safety_refusal"].agent, FoundryBackedAgent)


class FakeUsage:
    def model_dump(self):
        return {"prompt_tokens": 2, "completion_tokens": 3, "total_tokens": 5}


class FakeMessage:
    content = MockManagerInsightsAgent().raw_response()
    parsed = None


class FakeChoice:
    finish_reason = "stop"
    message = FakeMessage()


class FakeCompletion:
    id = "chatcmpl-test"
    choices = [FakeChoice()]
    usage = FakeUsage()


class FakeCompletions:
    def __init__(self) -> None:
        self.kwargs: dict[str, Any] | None = None

    def create(self, **kwargs: Any) -> FakeCompletion:
        self.kwargs = kwargs
        return FakeCompletion()


class FakeOpenAIClient:
    def __init__(self) -> None:
        completions = FakeCompletions()
        self.fake_completions = completions
        self.chat = type(
            "Chat",
            (),
            {"completions": completions},
        )()


class FakeProjectClient:
    def __init__(self) -> None:
        self.openai_client = FakeOpenAIClient()

    def get_openai_client(self) -> FakeOpenAIClient:
        return self.openai_client


def test_foundry_model_client_uses_project_openai_client_and_schema_format():
    fake_project = FakeProjectClient()
    client = FoundryModelClient(
        make_foundry_config(),
        project_client_factory=lambda: fake_project,
    )

    response = client.generate_json(
        agent_name="Manager Insights Agent",
        system_prompt="Return JSON.",
        user_payload={"team_id": "TEAM-SOC-A"},
        output_schema=ManagerInsight,
    )

    kwargs = fake_project.openai_client.fake_completions.kwargs
    assert response.request_id == "chatcmpl-test"
    assert response.model_deployment == "gpt-4o-mini"
    assert response.token_usage == {"prompt_tokens": 2, "completion_tokens": 3, "total_tokens": 5}
    assert kwargs is not None
    assert kwargs["model"] == "gpt-4o-mini"
    assert kwargs["response_format"] == {"type": "json_object"}
    assert kwargs["messages"][0]["content"] == "Return JSON."
